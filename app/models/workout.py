from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Float, String,
    DateTime, ForeignKey
)
from sqlalchemy.orm import relationship

from app.core.database import Base

# ---------------------------------------------------------------------------
# Workout (parent)
# ---------------------------------------------------------------------------

class Workout(Base):
    """
    One row per /extract-workout request.
    Stores the session-level metadata and the original raw text.
    """
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)

    # Mirrors WorkoutData fields
    workout_type           = Column(String, nullable=True)
    total_duration_minutes = Column(Float,  nullable=True)
    summary                = Column(String, nullable=True)

    # The original text the user submitted, kept for audit / reprocessing
    raw_text = Column(String, nullable=False)

    # Automatically set to UTC insertion time — useful for history queries
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # One Workout → many Exercise rows.
    # cascade="all, delete-orphan" means deleting a Workout also deletes
    # all its child Exercise rows automatically.
    exercises = relationship(
        "Exercise",
        back_populates="workout",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Workout id={self.id} type={self.workout_type!r} created_at={self.created_at}>"


# ---------------------------------------------------------------------------
# Exercise (child)
# ---------------------------------------------------------------------------

class Exercise(Base):
    """
    One row per exercise inside a workout session.
    Always belongs to exactly one Workout via the foreign key.
    """
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key back to the parent Workout row
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False, index=True)

    # Mirrors Exercise Pydantic schema fields
    name               = Column(String, nullable=False)
    sets               = Column(Integer, nullable=True)
    reps               = Column(Integer, nullable=True)
    weight_kg          = Column(Float,   nullable=True)
    duration_minutes   = Column(Float,   nullable=True)
    distance_km        = Column(Float,   nullable=True)
    notes              = Column(String,  nullable=True)

    # Back-reference so you can do exercise_instance.workout
    workout = relationship("Workout", back_populates="exercises")

    def __repr__(self) -> str:
        return f"<Exercise id={self.id} name={self.name!r} workout_id={self.workout_id}>"