# services/experiment_svc.py

import hashlib
import random
from datetime import datetime
from db.models import (
    Experiment, ExperimentSegment,
    UserExperimentAssignment, UserSegmentMembership
)
from services.banner_mixture import (
    get_banner_mixture_cache,
    set_banner_mixture_cache,
    generate_banner_mixture
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload


class ExperimentService:

    def __init__(self, db):
        self.db = db

    def create_experiment(self, name, variants, segmentIDs, status="active"):
        total_weight = sum(v["weight"] for v in variants)
        if total_weight != 100:
            raise ValueError("Variant weights must sum to 100")

        try:
            experiment = Experiment(
                name=name,
                variants=variants,
                status=status
            )
            self.db.add(experiment)
            self.db.commit()
            self.db.refresh(experiment)

        except IntegrityError:
            self.db.rollback()
            experiment = self.db.query(Experiment).filter(Experiment.name == name).first()

        # link segments — runs whether experiment is new or existing
        for seg_id in segmentIDs:
            existing_link = self.db.query(ExperimentSegment).filter(
                ExperimentSegment.experimentID == experiment.experimentID,
                ExperimentSegment.segmentID == seg_id
            ).first()
            if not existing_link:
                self.db.add(ExperimentSegment(
                    experimentID=experiment.experimentID,
                    segmentID=seg_id
                ))
        self.db.commit()
        return experiment


    def assign_variant(self, user_id, experiment):
        """Assign variant based on user ID hash."""
        key = f"{user_id}:{experiment.experimentID}"
        bucket = int(hashlib.md5(key.encode()).hexdigest(), 16) % 100

        cumulative = 0
        for variant in experiment.variants:
            cumulative += variant["weight"]
            if bucket < cumulative:
                return variant
        
        # Fallback to last variant (should not reach here with proper weights)
        return experiment.variants[-1]


    def _get_active_experiments_with_segments(self):
        """
        Single query that fetches all active experiments
        AND their segment links in one shot via JOIN.
        Replaces the previous pattern of fetching experiments
        then lazily loading exp.segments per experiment.
        """
        return self.db.query(Experiment)\
            .options(joinedload(Experiment.segments))\
            .filter(Experiment.status == "active")\
            .all()


    def get_banner_experiments(self, user_id):
        segments = self.db.query(UserSegmentMembership)\
            .filter(UserSegmentMembership.user_id == user_id).all()

        segmentIDs = set(s.segmentID for s in segments)      # ✅ set for O(1) lookup

        experiments = self._get_active_experiments_with_segments()  # ✅ single query

        banner_experiments = []

        for exp in experiments:
            target_segments = {es.segmentID for es in exp.segments}  # already loaded, no query

            if target_segments & segmentIDs:                  # set intersection, O(1)
                variant = self.assign_variant(user_id, exp)

                if isinstance(variant, dict) and "banners" in variant:
                    banner_experiments.append({
                        "experimentID": exp.experimentID,
                        "name": exp.name,
                        "variant_name": variant["name"],
                        "banners": variant["banners"]
                    })

        return banner_experiments



    def generate_user_banner_mixture(self, user_id):
        """
        Generate or retrieve cached banner mixture for user.
        
        Algorithm:
        1. Check cache
        2. If cache miss, collect all banners from applicable experiments
        3. Randomly select N banners from pool
        4. Store in cache with TTL
        
        Returns:
            Dict with banners, assigned_at, expires_at, source_experiments
            or None if no banner experiments found
        """
        # Step 1: Check cache
        cached_mixture = get_banner_mixture_cache(user_id)
        if cached_mixture is not None:
            return cached_mixture
        
        # Step 2: Get all applicable banner experiments
        banner_experiments = self.get_banner_experiments(user_id)
        
        if not banner_experiments:
            # No banner experiments for this user
            return None
        
        # Step 3: Collect all banners from all applicable experiments
        banner_pool = set()
        source_info = []
        
        for item in banner_experiments:
            banners = item["banners"]
            banner_pool.update(banners)
            source_info.append({
                "experiment_id": item["experimentID"],
                "name": item["name"],
                "variant": item["variant_name"],
                "contributed_banners": banners
            })
        
        # Step 4: Generate mixture (random selection without replacement)
        selected_banners = generate_banner_mixture(list(banner_pool))
        
        # Step 5: Cache it
        mixture = set_banner_mixture_cache(user_id, selected_banners, source_info)
        
        return mixture


    def get_user_experiments(self, user_id):
        segments = self.db.query(UserSegmentMembership)\
            .filter(UserSegmentMembership.user_id == user_id).all()

        segmentIDs = set(s.segmentID for s in segments)      

        experiments = self._get_active_experiments_with_segments()  

        results = []

        for exp in experiments:
            target_segments = {es.segmentID for es in exp.segments}  

            if target_segments & segmentIDs:                  
                variant = self.assign_variant(user_id, exp)
                results.append({
                    "experimentID": exp.experimentID,
                    "name": exp.name,
                    "variant": variant["name"]
                })

        return results