# services/experiment_svc.py

import hashlib
from db.models import (
    Experiment, ExperimentSegment,
    UserExperimentAssignment, UserSegmentMembership
)
from sqlalchemy.exc import IntegrityError



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

            for seg_id in segmentIDs:
                self.db.add(
                    ExperimentSegment(
                        experimentID=experiment.experimentID,
                        segmentID=seg_id
                    )
                )
            self.db.commit()
            return experiment

        except IntegrityError:
            self.db.rollback()
            return self.db.query(Experiment).filter(Experiment.name == name).first()


    def assign_variant(self, user_id, experiment):
        key = f"{user_id}:{experiment.experimentID}"
        bucket = int(hashlib.md5(key.encode()).hexdigest(), 16) % 100

        cumulative = 0
        for variant in experiment.variants:
            cumulative += variant["weight"]
            if bucket < cumulative:
                return variant["name"]

    def get_user_experiments(self, user_id):
        segments = self.db.query(UserSegmentMembership)\
            .filter(UserSegmentMembership.user_id == user_id).all()

        segmentIDs = [s.segmentID for s in segments]

        experiments = self.db.query(Experiment)\
            .filter(Experiment.status == "active").all()

        results = []

        for exp in experiments:
            target_segments = [es.segmentID for es in exp.segments]
            if any(s in segmentIDs for s in target_segments):
                variant = self.assign_variant(user_id, exp)
                results.append({
                    "experimentID": exp.experimentID,
                    "variant": variant
                })

        return results