import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from groq import Groq, APIConnectionError, APIStatusError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.workout import Workout, Exercise as ExerciseORM
from app.schemas.workout import WorkoutRequest, WorkoutResponse, WorkoutData

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
router = APIRouter()

groq_client = Groq(api_key=settings.GROQ_API_KEY)
# Atualizado para o modelo mais recente!
GROQ_MODEL  = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """
You are a precise fitness data extraction engine.

Your ONLY job is to read a raw workout description written by a user and convert it into a structured JSON object.

STRICT OUTPUT RULES — violating any of these makes your response useless:
1. Output RAW JSON only. No markdown. No code fences. No backticks. No explanation.
2. Your entire response must be a single, valid JSON object and nothing else.
3. If a field cannot be found in the text, use null — never guess or invent values.
4. All weights must be converted and stored in kilograms (kg). If the user writes lbs, convert it.
5. All distances must be stored in kilometers (km). If the user writes miles, convert it.

The JSON object you return must match this exact schema:
{
  "workout_type": "string or null",
  "total_duration_minutes": "number or null",
  "exercises": [
    {
      "name": "string",
      "sets": "integer or null",
      "reps": "integer or null",
      "weight_kg": "float or null",
      "duration_minutes": "float or null",
      "distance_km": "float or null",
      "notes": "string or null"
    }
  ],
  "summary": "string or null"
}

Remember: RAW JSON only. Start your response with '{' and end it with '}'.
"""

# ---------------------------------------------------------------------------
# DB Persistence Helper
# ---------------------------------------------------------------------------

def persist_workout(db: Session, raw_text: str, workout_data: WorkoutData) -> Workout:
    """
    Converts validated Pydantic WorkoutData into ORM objects and writes them
    to the database in a single atomic transaction.
    """
    # --- Build the parent Workout row ---
    db_workout = Workout(
        raw_text               = raw_text,
        workout_type           = workout_data.workout_type,
        total_duration_minutes = workout_data.total_duration_minutes,
        summary                = workout_data.summary,
    )

    # --- Build child Exercise rows and attach them to the parent ---
    for exercise in workout_data.exercises:
        db_exercise = ExerciseORM(
            name             = exercise.name,
            sets             = exercise.sets,
            reps             = exercise.reps,
            weight_kg        = exercise.weight_kg,
            duration_minutes = exercise.duration_minutes,
            distance_km      = exercise.distance_km,
            notes            = exercise.notes,
        )
        db_workout.exercises.append(db_exercise)

    # --- Persist: add → flush → commit → refresh ---
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)

    logger.info(
        "Persisted Workout id=%s with %d exercise(s).",
        db_workout.id,
        len(db_workout.exercises)
    )
    return db_workout


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post(
    "/extract-workout",
    response_model=WorkoutResponse,
    summary="Extract structured workout data from raw text using Groq AI",
    tags=["Workout"]
)
async def extract_workout(
    payload: WorkoutRequest,
    db: Session = Depends(get_db)   # ← session is created, yielded, and closed per request
):
    """
    Full pipeline:
      1. Validate raw text (Pydantic, handled automatically).
      2. Send to Groq / Llama 3.1 with strict JSON system prompt.
      3. Parse raw JSON string → Python dict.
      4. Validate dict against WorkoutData Pydantic schema.
      5. Persist Workout + Exercise rows to SQLite (new step).
      6. Return identical Pydantic response envelope to the client.
    """

    # === Step 1 – Call Groq ===
    try:
        logger.info("Sending request to Groq API (model: %s)", GROQ_MODEL)
        chat_completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": payload.raw_text}
            ]
        )
    except APIConnectionError as e:
        logger.error("Groq connection error: %s", e)
        raise HTTPException(status_code=503, detail="Could not reach the Groq API.")
    except APIStatusError as e:
        logger.error("Groq status error %s: %s", e.status_code, e.message)
        raise HTTPException(status_code=e.status_code, detail=f"Groq API error: {e.message}")

    # === Step 2 – Parse JSON ===
    raw_json_string = chat_completion.choices[0].message.content
    logger.debug("Raw Groq response: %s", raw_json_string)

    try:
        extracted_dict = json.loads(raw_json_string)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed. Raw output: %s", raw_json_string)
        raise HTTPException(
            status_code=422,
            detail=f"AI returned non-JSON output. Parser error: {e}"
        )

    # === Step 3 – Validate against Pydantic schema ===
    try:
        workout_data = WorkoutData(**extracted_dict)
    except Exception as e:
        logger.error("Pydantic validation failed: %s", e)
        raise HTTPException(
            status_code=422,
            detail=f"Extracted data did not match expected schema: {e}"
        )

    # === Step 4 – Persist to SQLite ===
    try:
        persist_workout(db=db, raw_text=payload.raw_text, workout_data=workout_data)
    except Exception as e:
        db.rollback()
        logger.error("Database write failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Extraction succeeded but database write failed: {e}"
        )

    # === Step 5 – Return identical response envelope ===
    return WorkoutResponse(
        status="success",
        received_text=payload.raw_text,
        extracted_data=workout_data
    )