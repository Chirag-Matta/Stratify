# services/experiment_svc.py

import hashlib
from db.models import (
    Experiment, ExperimentSegment,
    UserExperimentAssignment, UserSegmentMembership
)


class ExperimentService:

    def __init__(self, db):
        self.db = db

    def create_experiment(self, name, variants, segment_ids, status="active"):
        total_weight = sum(v["weight"] for v in variants)
        if total_weight != 100:
            raise ValueError("Variant weights must sum to 100")

        experiment = Experiment(
            name=name,
            variants=variants,
            status=status
        )
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)

        for seg_id in segment_ids:
            self.db.add(
                ExperimentSegment(
                    experiment_id=experiment.id,
                    segment_id=seg_id
                )
            )

        self.db.commit()
        return experiment

    def assign_variant(self, user_id, experiment):
        key = f"{user_id}:{experiment.id}"
        bucket = int(hashlib.md5(key.encode()).hexdigest(), 16) % 100

        cumulative = 0
        for variant in experiment.variants:
            cumulative += variant["weight"]
            if bucket < cumulative:
                return variant["name"]

    def get_user_experiments(self, user_id):
        segments = self.db.query(UserSegmentMembership)\
            .filter(UserSegmentMembership.user_id == user_id).all()

        segment_ids = [s.segment_id for s in segments]

        experiments = self.db.query(Experiment)\
            .filter(Experiment.status == "active").all()

        results = []

        for exp in experiments:
            target_segments = [es.segment_id for es in exp.segments]
            if any(s in segment_ids for s in target_segments):
                variant = self.assign_variant(user_id, exp)
                results.append({
                    "experiment_id": exp.id,
                    "variant": variant
                })

        return results