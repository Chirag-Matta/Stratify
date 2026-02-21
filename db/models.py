# db/models.py
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, JSON, ForeignKey,
    UniqueConstraint, Float, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Order(Base):
    __tablename__ = "orders"

    orderID = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    city = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Segment(Base):
    __tablename__ = "segments"

    segmentID = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    rules = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    experiments = relationship("ExperimentSegment", back_populates="segment")

class Experiment(Base):
    __tablename__ = "experiments"

    experimentID = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    status = Column(String, default="draft")
    variants = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    segments = relationship("ExperimentSegment", back_populates="experiment")

class ExperimentSegment(Base):
    __tablename__ = "experiment_segments"

    experimentID = Column(String, ForeignKey("experiments.experimentID"), primary_key=True)
    segmentID = Column(String, ForeignKey("segments.segmentID"), primary_key=True)

    experiment = relationship("Experiment", back_populates="segments")
    segment = relationship("Segment", back_populates="experiments")

class UserSegmentMembership(Base):
    __tablename__ = "user_segment_memberships"

    user_id = Column(String, primary_key=True)
    segmentID = Column(String, ForeignKey("segments.segmentID"), primary_key=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "segmentID"),
    )

class UserExperimentAssignment(Base):
    __tablename__ = "user_experiment_assignments"

    user_id = Column(String, primary_key=True)
    experimentID = Column(String, ForeignKey("experiments.experimentID"), primary_key=True)
    variant = Column(String)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "experimentID"),
    )

def create_tables(database_url):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)