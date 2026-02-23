#!/usr/bin/env python3
# test_data_setup.py
"""
Automated test data setup script for Daffodil system.
Creates segments, experiments, users, and populates test data.
"""

import requests
import json
import time
from typing import Dict

# Configuration
API_BASE_URL = "http://localhost:8000"
RETRY_ATTEMPTS = 3
DELAY_BETWEEN_REQUESTS = 0.1

# Storage for IDs
segment_ids = {}
experiment_ids = {}

def log(message: str, level: str = "INFO"):
    """Print formatted log message."""
    print(f"[{level}] {message}")

def make_request(method: str, endpoint: str, data: dict = None) -> Dict:
    """Make HTTP request with retry logic."""
    url = f"{API_BASE_URL}{endpoint}"
    
    for attempt in range(RETRY_ATTEMPTS):
        try:
            if method == "POST":
                response = requests.post(url, json=data, timeout=5)
            elif method == "GET":
                response = requests.get(url, timeout=5)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < RETRY_ATTEMPTS - 1:
                log(f"Request failed, retrying... ({attempt + 1}/{RETRY_ATTEMPTS})", "WARN")
                time.sleep(1)
            else:
                log(f"Request failed after {RETRY_ATTEMPTS} attempts: {e}", "ERROR")
                raise
    
    return {}

def create_segments():
    """Create all 13 segments."""
    log("=" * 60)
    log("CREATING SEGMENTS (13 TOTAL)", "START")
    log("=" * 60)
    
    segments_config = [
        {
            "name": "new_user",
            "description": "User who has never placed an order",
            "rules": {
                "operator": "AND",
                "conditions": [{"field": "is_new_user", "op": "eq", "value": True}]
            }
        },
        {
            "name": "recently_active_user",
            "description": "User who has placed at least 1 order in the past 7 days",
            "rules": {
                "operator": "AND",
                "conditions": [{"field": "days_since_last_order", "op": "lt", "value": 7}]
            }
        },
        {
            "name": "low_monthly_active_user",
            "description": "User not active in past 7 days but in past 30 days",
            "rules": {
                "operator": "AND",
                "conditions": [
                    {"field": "days_since_last_order", "op": "gte", "value": 7},
                    {"field": "days_since_last_order", "op": "lt", "value": 30}
                ]
            }
        },
        {
            "name": "dormant_user",
            "description": "User who has not placed an order in the past 14 days",
            "rules": {
                "operator": "AND",
                "conditions": [{"field": "days_since_last_order", "op": "gte", "value": 14}]
            }
        },
        {
            "name": "light_user",
            "description": "User with 1-5 lifetime orders",
            "rules": {
                "operator": "AND",
                "conditions": [
                    {"field": "total_orders", "op": "gte", "value": 1},
                    {"field": "total_orders", "op": "lte", "value": 5}
                ]
            }
        },
        {
            "name": "regular_user",
            "description": "User with 6-15 lifetime orders",
            "rules": {
                "operator": "AND",
                "conditions": [
                    {"field": "total_orders", "op": "gte", "value": 6},
                    {"field": "total_orders", "op": "lte", "value": 15}
                ]
            }
        },
        {
            "name": "power_user",
            "description": "User with 25+ orders in the past 23 days",
            "rules": {
                "operator": "AND",
                "conditions": [{"field": "order_count_last_23_days", "op": "gte", "value": 25}]
            }
        },
        {
            "name": "high_ltv_user",
            "description": "User with lifetime value (LTV) of 1500 or more",
            "rules": {
                "operator": "AND",
                "conditions": [{"field": "ltv", "op": "gte", "value": 1500}]
            }
        },
        {
            "name": "hsr_layout_resident",
            "description": "User whose most recent order is from HSR Layout",
            "rules": {
                "operator": "AND",
                "conditions": [{"field": "city", "op": "eq", "value": "HSR Layout"}]
            }
        },
        {
            "name": "whitefield_resident",
            "description": "User whose most recent order is from Whitefield",
            "rules": {
                "operator": "AND",
                "conditions": [{"field": "city", "op": "eq", "value": "Whitefield"}]
            }
        },
        {
            "name": "koramangala_resident",
            "description": "User whose most recent order is from Koramangala",
            "rules": {
                "operator": "AND",
                "conditions": [{"field": "city", "op": "eq", "value": "Koramangala"}]
            }
        },
        {
            "name": "vip_user",
            "description": "User with high LTV (1500+) and recently active (< 7 days)",
            "rules": {
                "operator": "AND",
                "conditions": [
                    {"field": "ltv", "op": "gte", "value": 1500},
                    {"field": "days_since_last_order", "op": "lt", "value": 7}
                ]
            }
        },
        {
            "name": "at_risk_vip",
            "description": "User with high LTV (1500+) but dormant (14+ days)",
            "rules": {
                "operator": "AND",
                "conditions": [
                    {"field": "ltv", "op": "gte", "value": 1500},
                    {"field": "days_since_last_order", "op": "gte", "value": 14}
                ]
            }
        }
    ]
    
    for i, config in enumerate(segments_config, 1):
        try:
            response = make_request("POST", "/segments", config)
            segment_id = response.get("segmentID")
            segment_ids[config["name"]] = segment_id
            log(f"✓ Created segment {i}/13: {config['name']} (ID: {segment_id[:8]}...)")
            time.sleep(DELAY_BETWEEN_REQUESTS)
        except Exception as e:
            log(f"✗ Failed to create segment {config['name']}: {e}", "ERROR")
            raise
    
    log(f"✓ All 13 segments created!", "SUCCESS")

def create_experiments():
    """Create all 18 experiments."""
    log("=" * 60)
    log("CREATING EXPERIMENTS (18 TOTAL)", "START")
    log("=" * 60)
    
    experiments_config = [
        {
            "name": "new_user_onboarding_banners",
            "variants": [
                {"name": "banners_1_2_3", "banners": [1, 2, 3], "weight": 50},
                {"name": "banners_4_5_6", "banners": [4, 5, 6], "weight": 50}
            ],
            "segments": ["new_user"]
        },
        {
            "name": "recently_active_user_banners",
            "variants": [{"name": "banners_2_3_5", "banners": [2, 3, 5], "weight": 100}],
            "segments": ["recently_active_user"]
        },
        {
            "name": "low_monthly_active_banners",
            "variants": [{"name": "banners_7_8_9", "banners": [7, 8, 9], "weight": 100}],
            "segments": ["low_monthly_active_user"]
        },
        {
            "name": "dormant_user_banners",
            "variants": [{"name": "banners_10_11_12", "banners": [10, 11, 12], "weight": 100}],
            "segments": ["dormant_user"]
        },
        {
            "name": "power_user_banners",
            "variants": [
                {"name": "banners_1_2_3", "banners": [1, 2, 3], "weight": 50},
                {"name": "banners_1_3_5", "banners": [1, 3, 5], "weight": 50}
            ],
            "segments": ["power_user"]
        },
        {
            "name": "light_user_engagement_banners",
            "variants": [{"name": "banners_3_4_6", "banners": [3, 4, 6], "weight": 100}],
            "segments": ["light_user"]
        },
        {
            "name": "regular_user_discovery_banners",
            "variants": [{"name": "banners_2_4_7", "banners": [2, 4, 7], "weight": 100}],
            "segments": ["regular_user"]
        },
        {
            "name": "hsr_layout_banners",
            "variants": [{"name": "banners_5_6_7", "banners": [5, 6, 7], "weight": 100}],
            "segments": ["hsr_layout_resident"]
        },
        {
            "name": "whitefield_banners",
            "variants": [{"name": "banners_8_9_10", "banners": [8, 9, 10], "weight": 100}],
            "segments": ["whitefield_resident"]
        },
        {
            "name": "koramangala_banners",
            "variants": [{"name": "banners_11_12_13", "banners": [11, 12, 13], "weight": 100}],
            "segments": ["koramangala_resident"]
        },
        {
            "name": "high_ltv_user_banners",
            "variants": [{"name": "banners_1_2_14", "banners": [1, 2, 14], "weight": 100}],
            "segments": ["high_ltv_user"]
        },
        {
            "name": "vip_user_banners",
            "variants": [{"name": "banners_1_14_15", "banners": [1, 14, 15], "weight": 100}],
            "segments": ["vip_user"]
        },
        {
            "name": "at_risk_vip_banners",
            "variants": [{"name": "banners_16_17_18", "banners": [16, 17, 18], "weight": 100}],
            "segments": ["at_risk_vip"]
        },
        {
            "name": "pizza_category_visibility",
            "variants": [
                {"name": "control", "weight": 50},
                {"name": "show_pizza_tile", "weight": 50}
            ],
            "segments": ["power_user"]
        },
        {
            "name": "dormant_user_discount",
            "variants": [
                {"name": "control", "weight": 20},
                {"name": "show_100_rupees_discount", "weight": 80}
            ],
            "segments": ["dormant_user"]
        },
        {
            "name": "dormant_user_content_strategy",
            "variants": [
                {"name": "trending_popular", "weight": 50},
                {"name": "personalized_past_favorites", "weight": 50}
            ],
            "segments": ["dormant_user"]
        },
        {
            "name": "power_user_premium_features",
            "variants": [
                {"name": "control", "weight": 50},
                {"name": "priority_delivery", "weight": 50}
            ],
            "segments": ["power_user"]
        },
        {
            "name": "vip_priority_support",
            "variants": [
                {"name": "standard_support", "weight": 50},
                {"name": "vip_priority_support", "weight": 50}
            ],
            "segments": ["vip_user"]
        }
    ]
    
    for i, config in enumerate(experiments_config, 1):
        try:
            # Map segment names to IDs
            segment_ids_list = [segment_ids[seg] for seg in config["segments"]]
            
            payload = {
                "name": config["name"],
                "variants": config["variants"],
                "segmentIDs": segment_ids_list
            }
            
            response = make_request("POST", "/experiments", payload)
            exp_id = response.get("experimentID")
            experiment_ids[config["name"]] = exp_id
            log(f"✓ Created experiment {i}/18: {config['name']} (ID: {exp_id[:8]}...)")
            time.sleep(DELAY_BETWEEN_REQUESTS)
        except Exception as e:
            log(f"✗ Failed to create experiment {config['name']}: {e}", "ERROR")
            raise
    
    log(f"✓ All 18 experiments created!", "SUCCESS")

def create_test_users():
    """Create 5 test users."""
    log("=" * 60)
    log("CREATING TEST USERS (5 TOTAL)", "START")
    log("=" * 60)
    
    users = [
        {"user_id": "user_lisa_new", "name": "Lisa (New User)"},
        {"user_id": "user_sarah_power_hsr", "name": "Sarah (Power User)"},
        {"user_id": "user_tom_low_monthly_hsr", "name": "Tom (Low Monthly Active)"},
        {"user_id": "user_john_at_risk_vip", "name": "John (At-Risk VIP)"},
        {"user_id": "user_mike_regular_whitefield", "name": "Mike (Regular User)"}
    ]
    
    for i, user in enumerate(users, 1):
        try:
            response = make_request("POST", "/users", {"user_id": user["user_id"]})
            log(f"✓ Created user {i}/5: {user['name']} (ID: {user['user_id']})")
            time.sleep(DELAY_BETWEEN_REQUESTS)
        except Exception as e:
            log(f"✗ Failed to create user {user['name']}: {e}", "ERROR")
            raise
    
    log(f"✓ All 5 users created!", "SUCCESS")

def populate_test_data():
    """Populate test data for users."""
    log("=" * 60)
    log("POPULATING TEST DATA", "START")
    log("=" * 60)
    
    # User 2: Sarah (Power User - 28 orders in past 23 days)
    log("Populating Sarah (Power User): 28 orders...")
    for i in range(28):
        try:
            make_request("POST", "/orders", {
                "user_id": "user_sarah_power_hsr",
                "amount": 65,
                "city": "HSR Layout"
            })
            time.sleep(0.05)
        except Exception as e:
            log(f"✗ Failed to create order for Sarah: {e}", "ERROR")
    log("✓ Sarah: 28 orders created")
    
    # User 3: Tom (Low Monthly Active - 3 orders)
    log("Populating Tom (Low Monthly Active): 3 orders...")
    for i in range(3):
        try:
            make_request("POST", "/orders", {
                "user_id": "user_tom_low_monthly_hsr",
                "amount": 85,
                "city": "HSR Layout"
            })
            time.sleep(0.1)
        except Exception as e:
            log(f"✗ Failed to create order for Tom: {e}", "ERROR")
    log("✓ Tom: 3 orders created (will be low_monthly_active)")
    
    # User 4: John (At-Risk VIP - 35 orders with high value)
    log("Populating John (At-Risk VIP): 35 orders...")
    for i in range(35):
        try:
            make_request("POST", "/orders", {
                "user_id": "user_john_at_risk_vip",
                "amount": 58,
                "city": "Bangalore"
            })
            time.sleep(0.05)
        except Exception as e:
            log(f"✗ Failed to create order for John: {e}", "ERROR")
    log("✓ John: 35 orders created (LTV = 2030)")
    
    # User 5: Mike (Regular User - 10 orders)
    log("Populating Mike (Regular User): 10 orders...")
    for i in range(10):
        try:
            make_request("POST", "/orders", {
                "user_id": "user_mike_regular_whitefield",
                "amount": 75,
                "city": "Whitefield"
            })
            time.sleep(0.1)
        except Exception as e:
            log(f"✗ Failed to create order for Mike: {e}", "ERROR")
    log("✓ Mike: 10 orders created")
    
    log(f"✓ All test data populated!", "SUCCESS")

def verify_setup():
    """Verify the setup by testing endpoints."""
    log("=" * 60)
    log("VERIFYING SETUP", "START")
    log("=" * 60)
    
    users = [
        ("user_lisa_new", "Lisa (New User)"),
        ("user_sarah_power_hsr", "Sarah (Power User)"),
        ("user_tom_low_monthly_hsr", "Tom (Low Monthly Active)"),
        ("user_john_at_risk_vip", "John (At-Risk VIP)"),
        ("user_mike_regular_whitefield", "Mike (Regular User)")
    ]
    
    for user_id, user_name in users:
        try:
            response = make_request("GET", f"/users/{user_id}/experiments")
            experiments = response.get("experiments", [])
            banner_mixture = response.get("banner_mixture", {})
            banners = banner_mixture.get("banners", [])
            
            log(f"✓ {user_name}:")
            log(f"  - Experiments assigned: {len(experiments)}")
            log(f"  - Banner mixture: {banners}")
            time.sleep(0.5)
        except Exception as e:
            log(f"✗ Failed to verify {user_name}: {e}", "ERROR")

def main():
    """Main execution."""
    try:
        log("🚀 DAFFODIL TEST DATA SETUP", "STARTUP")
        log(f"API URL: {API_BASE_URL}")
        log("")
        
        # Wait for server to be ready
        log("Waiting for server to be ready...")
        for i in range(10):
            try:
                requests.get(f"{API_BASE_URL}/users/dummy/experiments", timeout=1)
                break
            except:
                if i < 9:
                    time.sleep(1)
        
        create_segments()
        log("")
        create_experiments()
        log("")
        create_test_users()
        log("")
        populate_test_data()
        log("")
        verify_setup()
        
        log("")
        log("=" * 60)
        log("✨ SETUP COMPLETE! ✨", "SUCCESS")
        log("=" * 60)
        log("Database is ready for testing!")
        log("You can now run tests with:")
        log("  curl -X GET http://localhost:8000/users/user_sarah_power_hsr/experiments")
        
    except Exception as e:
        log(f"Setup failed: {e}", "CRITICAL")
        exit(1)

if __name__ == "__main__":
    main()