# Stratify — User Segmentation & Experimentation System

A production-ready POC for a **user segmentation and experimentation platform** built for a food delivery app. Enables David (and his engineering team) to run data-driven experiments, personalize user experiences, and auto-segment users based on their behavior in real time.

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Core Concepts](#core-concepts)
- [API Reference](#api-reference)
- [Getting Started](#getting-started)
- [Running the System](#running-the-system)
- [Example Use Cases](#example-use-cases)
- [Design Decisions](#design-decisions)

---

## System Overview

Stratify solves three key problems:

1. **Segment users dynamically** based on behavioral rules (orders placed, LTV, city, recency, etc.)
2. **Run multi-variant experiments** by targeting specific user segments
3. **React to events in real time** — when a user places an order, their segments update automatically

```
User places order → Kafka event → Consumer re-evaluates segments → Cache invalidated → Next API call returns fresh experiments
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Server                           │
│  POST /orders   GET /users/:id/experiments   POST /segments     │
└────────────┬─────────────────────┬───────────────────┬─────────┘
             │                     │                   │
             ▼                     ▼                   ▼
      ┌─────────────┐     ┌──────────────┐    ┌──────────────────┐
      │  Kafka Topic│     │  Redis Cache │    │   PostgreSQL DB  │
      │ order_placed│     │  (5 min TTL) │    │                  │
      └──────┬──────┘     └──────────────┘    │  users           │
             │                                │  orders          │
             ▼                                │  segments        │
      ┌─────────────┐                         │  experiments     │
      │  Consumer   │──────────────────────►  │  memberships     │
      │  (Worker)   │  refresh_user_segments  │  assignments     │
      └─────────────┘                         └──────────────────┘
             │
             ├─────────────────────────────────────┐
             │                                     │
             ▼                                     ▼
      ┌─────────────┐                      ┌─────────────────┐
      │  Cron Job   │  (batch refresh of   │  APScheduler    │
      │             │   dormant users)     │  (deferred      │
      └─────────────┘                      │   dormancy      │
                                           │   checks)       │
                                           └─────────────────┘
```

### Data Flow

1. **Segment Creation** — Admin defines rules (e.g., `orders_last_23_days >= 25`) via API
2. **Experiment Creation** — Experiments link to segments with weighted variants
3. **Order Placed** → Write to DB + Kafka publishes `order_placed` event + schedule deferred dormancy check
4. **Consumer** picks up event → recomputes user stats → updates `user_segment_memberships`
5. **Cache invalidated** for both experiments and banner mixture
6. **GET /experiments** — Checks Redis first; on miss, recomputes from Postgres and re-caches
7. **Deferred Dormancy Check** — 14 days (or DORMANCY_SECONDS in testing) after order, check if user is still dormant → if so, refresh segments

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **API** | FastAPI (Python) | Fast, async-ready, auto Swagger docs |
| **Primary DB** | PostgreSQL | Relational integrity for segments/experiments/users |
| **Cache** | Redis | Low-latency experiment lookups (5 min TTL for experiments, 24 hr for banner mixtures) |
| **Message Queue** | Apache Kafka | Durable, decoupled event streaming for real-time segment refresh |
| **Job Scheduler** | APScheduler | In-app deferred dormancy checks (survives restarts via Redis jobstore) |
| **Batch Jobs** | cron / manual | Periodic refresh for dormant users (complements APScheduler) |

---

## Project Structure

```
Stratify/
├── api/
│   └── routes.py              # All FastAPI endpoints
├── consumer/
│   └── consumer.py            # Kafka consumer — listens to order_placed events
├── cron/
│   └── refresh_segments.py    # Batch job for dormant user re-evaluation (optional)
├── db/
│   └── models.py              # SQLAlchemy models
├── services/
│   ├── segment_svc.py         # Segment CRUD + user membership refresh
│   ├── experiment_svc.py      # Experiment CRUD + variant assignment
│   ├── rule_engine.py         # Evaluates segment rules against user stats
│   ├── user_stats.py          # Computes live user metrics from orders
│   ├── banner_mixture.py      # Banner pool selection + Redis caching
│   ├── cache.py               # Experiment-level Redis cache helpers
│   ├── producer.py            # Kafka producer
│   ├── scheduler.py           # APScheduler configuration (Redis jobstore)
│   └── dormancy_check.py      # Deferred dormancy check callback
├── output/
│   └── setup.py               # Test data bootstrap script
├── docker-compose.yml         # Kafka setup
├── requirements.txt
└── .env                       # DATABASE_URL, REDIS_URL, KAFKA_SERVERS
```

---

## Core Concepts

### Segments

A **Segment** is a named group of users defined by a JSON rule tree. Rules support `AND`/`OR` operators and leaf conditions with operators: `gt`, `gte`, `lt`, `lte`, `eq`, `neq`, `in`, `not_in`.

**Example segment rule:**
```json
{
  "operator": "AND",
  "conditions": [
    { "field": "order_count_last_23_days", "op": "gte", "value": 25 }
  ]
}
```

**Supported fields in rule engine:**

| Field | Description |
|---|---|
| `total_orders` | Lifetime order count |
| `order_count_last_23_days` | Orders in past 23 days |
| `order_count_last_15_days` | Orders in past 15 days |
| `order_count_last_12_days` | Orders in past 12 days |
| `ltv` | Lifetime spend (sum of order amounts) |
| `seconds_since_last_order` | Seconds since most recent order |
| `city` | City of most recent order |
| `is_new_user` | Boolean — true if no orders ever |

### Experiments

An **Experiment** targets one or more segments and contains **weighted variants** (weights must sum to 100). Variant assignment is deterministic per user via MD5 hash bucketing — the same user always gets the same variant for a given experiment.

```json
{
  "name": "dormant_user_discount",
  "variants": [
    { "name": "control", "weight": 20 },
    { "name": "show_100_rupees_discount", "weight": 80 }
  ],
  "segmentIDs": ["<uuid>"]
}
```

### Real-time Segment Refresh

When a user places an order:
1. The API writes to Postgres and publishes an `order_placed` Kafka event
2. The consumer recomputes all segment memberships for that user
3. Redis caches (experiments + banner mixture) are invalidated
4. The next call to `GET /users/:id/experiments` gets fresh data

### Deferred Dormancy Checks

APScheduler provides a **robust alternative** to cron for checking dormancy:

1. When a user places an order, the API schedules a dormancy check job via APScheduler
2. The job is stored in Redis (survives app restarts)
3. Exactly 14 days later (or DORMANCY_SECONDS in testing), the job fires
4. The job checks: has the user placed any order since?
   - **Yes** → Skip (user is active)
   - **No** → Refresh segments (user is dormant)

This replaces the need for frequent cron runs and ensures dormancy checks happen at the exact right moment without batch delays.

**Configuration:**
- In `routes.py`, line: `DORMANCY_SECONDS = 90` (testing mode)
- For production, change to: `DORMANCY_DAYS = 14` and adjust the timedelta accordingly

### Banner Mixture

Banner experiments declare a `banners` array in their variant. When a user qualifies for multiple banner experiments, all eligible banners are pooled and 3 are randomly selected. This mixture is cached for 24 hours and invalidated on new orders.

---

## API Reference

### Register a User
```
POST /users
Body: { "user_id": "user_abc" }
```

### Get User Experiments
```
GET /users/{user_id}/experiments
```
Returns all active experiments the user is enrolled in, their assigned variant, and the resolved banner mixture. Served from Redis cache when available.

**Response:**
```json
{
  "user_id": "user_sarah_power_hsr",
  "source": "db",
  "experiments": [
    { "experimentID": "...", "name": "pizza_category_visibility", "variant": "show_pizza_tile" },
    { "experimentID": "...", "name": "power_user_premium_features", "variant": "priority_delivery" }
  ],
  "banner_mixture": {
    "banners": [1, 3, 5],
    "assigned_at": "2024-01-15T10:30:00Z",
    "expires_at": "2024-01-16T10:30:00Z",
    "ttl_seconds": 86400,
    "source_experiments": [...]
  }
}
```

### Create a Segment
```
POST /segments
Body:
{
  "name": "high_value_recent",
  "description": "Users with 13+ orders in 15 days and LTV > 1000",
  "rules": {
    "operator": "AND",
    "conditions": [
      { "field": "order_count_last_15_days", "op": "gte", "value": 13 },
      { "field": "ltv", "op": "gt", "value": 1000 }
    ]
  }
}
```

### Create an Experiment
```
POST /experiments
Body:
{
  "name": "my_experiment",
  "variants": [
    { "name": "control", "weight": 50 },
    { "name": "treatment", "weight": 50 }
  ],
  "segmentIDs": ["<segment-uuid>"]
}
```

### Place an Order
```
POST /orders
Body: { "user_id": "user_abc", "amount": 250, "city": "HSR Layout" }
```
Triggers three actions:
1. Writes order to database
2. Publishes `order_placed` Kafka event → consumer recomputes segments
3. Schedules a deferred dormancy check via APScheduler (fires in 14 days or DORMANCY_SECONDS)

All caches are immediately invalidated.

### Get Banner Mixture (Debug)
```
GET /users/{user_id}/banner_mixture
```

### Invalidate User Cache (Admin)
```
DELETE /users/{user_id}/cache
```
Clears both experiment and banner mixture caches.

---

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL running locally (or via Docker)
- Redis running locally
- Docker (for Kafka)

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd Stratify
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the root:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/your-db-name
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
KAFKA_SERVERS=localhost:9092
```

### 3. Start Kafka

```bash
docker-compose up -d
```

### 4. Start the API server

```bash
uvicorn api.routes:app --reload --port 8000
```

The scheduler starts automatically on app startup and manages deferred dormancy checks.

### 5. Start the Kafka consumer (separate terminal)

```bash
python consumer/consumer.py
```

### 6. (Optional) Run the cron job manually for batch dormancy refresh

```bash
python cron/refresh_segments.py
```

This is useful for backfilling or as a safety net, but with APScheduler in place, it's no longer the primary mechanism for dormancy detection.

---

## Running the System

### Bootstrap test data

This script creates 13 segments, 18 experiments, 5 test users, and populates realistic order histories:

```bash
python output/setup.py
```

### Test the API

```bash
# New user — no orders yet
curl http://localhost:8000/users/user_lisa_new/experiments

# Power user in HSR Layout — 28 orders
curl http://localhost:8000/users/user_sarah_power_hsr/experiments

# At-risk VIP — high LTV but dormant
curl http://localhost:8000/users/user_john_at_risk_vip/experiments
```

### Swagger UI

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for the full interactive API docs.

---

## Example Use Cases

The system supports all three use cases from the brief out of the box:

**Use Case 1 — Pizza tile for power users**
- Segment: `power_user` (`order_count_last_23_days >= 25`)
- Experiment: `pizza_category_visibility` (variant: `show_pizza_tile`)
- The client reads the variant and conditionally renders the pizza tile

**Use Case 2 — Tiered banner targeting**
- New users → `new_user_onboarding_banners` → `[Banner 1, 2, 3]`
- 10-order users → `regular_user_discovery_banners` → `[Banner 2, 4, 7]`
- 8-order users in HSR Layout → both `hsr_layout_banners` and order-count-based banners contribute to the final 3-banner mixture

**Use Case 3 — Dormant user win-back**
- Segment: `dormant_user` (`seconds_since_last_order >= 1209600` — 14 days in seconds)
- Experiments: `dormant_user_discount` (80% see the ₹100 off widget), `dormant_user_content_strategy` (personalized top picks)
- APScheduler checks this exactly 14 days after each order; cron job available as a safety net

---

## Design Decisions

### Why APScheduler for Dormancy?

1. **Precision**: Dormancy check fires at exactly the right moment (14 days post-order), not at batch boundaries
2. **Resilience**: Jobs stored in Redis survive app restarts
3. **Efficiency**: No need for constant polling or cron overhead
4. **Per-user tracking**: Each user gets their own deferred job, keyed by user_id

### Why Keep the Cron Job?

1. **Safety net**: Backfill for users who were dormant before APScheduler was deployed
2. **Manual refresh**: Ad-hoc re-evaluation if needed (e.g., after rule changes)
3. **Batch compliance**: Some orgs require batch verification of dormancy status

### Experiment Caching Strategy

- **5-minute TTL** for experiment assignments (short-lived; re-computed on cache miss)
- **24-hour TTL** for banner mixture (user experience consistency; re-randomized only if user gains/loses segments)
- Cache invalidation is **immediate** on order placement (ensures real-time behavior for dormancy/segment changes)

### Why Separate Banner Mixture Cache?

Banner experiments involve random selection (3 out of N banners). Caching the result for 24 hours ensures:
- Consistent user experience (same banners across multiple visits)
- Reduced computation (no re-randomization)
- Invalidation on segment changes (re-randomize only when user gains/loses eligibility)

---
