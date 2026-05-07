from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Nested Models (building blocks of the extracted workout)
# ---------------------------------------------------------------------------

class Exercise(BaseModel):
    """Represents a single exercise parsed from the raw workout text."""
    name: str = Field(..., description="Name of the exercise, e.g. 'Bench Press'")
    sets: int | None = Field(None, description="Number of sets performed")
    reps: int | None = Field(None, description="Number of reps per set")
    weight_kg: float | None = Field(None, description="Weight used in kilograms")
    duration_minutes: float | None = Field(None, description="Duration in minutes, for cardio exercises")
    distance_km: float | None = Field(None, description="Distance in km, for running/cycling")
    notes: str | None = Field(None, description="Any extra detail that doesn't fit above")


class WorkoutData(BaseModel):
    """The complete structured workout extracted from the raw text."""
    workout_type: str | None = Field(None, description="General category, e.g. 'Strength', 'Cardio', 'Mixed'")
    total_duration_minutes: float | None = Field(None, description="Total session duration if mentioned")
    exercises: list[Exercise] = Field(default_factory=list, description="List of all exercises found")
    summary: str | None = Field(None, description="One-sentence summary of the session")


# ---------------------------------------------------------------------------
# Request / Response Envelope Models (used by the FastAPI route)
# ---------------------------------------------------------------------------

class WorkoutRequest(BaseModel):
    raw_text: str = Field(
        ...,
        min_length=10,
        description="The raw, unstructured workout text to be parsed.",
        examples=["Ran 5km in 25 minutes, then did 3 sets of 10 pull-ups at bodyweight."]
    )


class WorkoutResponse(BaseModel):
    status: str
    received_text: str
    extracted_data: WorkoutData | None = None