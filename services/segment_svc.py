# services/segment_svc.py

from db.models import Segment, UserSegmentMembership
from services.rule_engine import evaluate
from services.user_stats import UserStatsService
from sqlalchemy.exc import IntegrityError


class SegmentService:

    def __init__(self, db):
        self.db = db

    def create_segment(self, name, description, rules):
        try:
            segment = Segment(name=name, description=description, rules=rules)
            self.db.add(segment)
            self.db.commit()
            self.db.refresh(segment)
            return segment
        except IntegrityError:
            self.db.rollback()
            # return the existing segment instead
            return self.db.query(Segment).filter(Segment.name == name).first()

    def get_all_segments(self):
        return self.db.query(Segment).all()

    def refresh_user_segments(self, user_id):
        stats = UserStatsService(self.db).get_stats(user_id)
        segments = self.get_all_segments()

        matched = []
        for segment in segments:
            if evaluate(segment.rules, stats):
                matched.append(segment.segmentID)

        # delete old
        self.db.query(UserSegmentMembership)\
            .filter(UserSegmentMembership.user_id == user_id)\
            .delete()

        # insert new
        for seg_id in matched:
            self.db.add(UserSegmentMembership(user_id=user_id, segmentID=seg_id))

        self.db.commit()
        return matched