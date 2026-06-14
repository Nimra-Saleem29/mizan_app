"""
Wakeel وکیل — Know Your Rights Scenario Router
================================================
Guided decision-tree for common Pakistani legal situations.

Endpoints:
  GET  /scenario/types                  — list all scenarios
  POST /scenario/start                  — start a session
  POST /scenario/{session_id}/answer    — submit yes/no answer
  GET  /scenario/{session_id}           — get session state
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel
from supabase.client import AsyncClient

from database import get_supabase
from models.schemas import LanguageCode
from services.scenario_engine import (
    get_first_step,
    get_next_step,
    get_scenario_list,
    get_step,
)

router = APIRouter()


class StartRequest(BaseModel):
    scenario_type: str
    language: LanguageCode = "urdu"
    user_id: Optional[UUID] = None


class AnswerRequest(BaseModel):
    step_id: str
    answer: str   # "yes" | "no" | "unsure"
    user_id: Optional[UUID] = None


# ── In-memory session store (fine for dev — use Redis in production) ──────────
_sessions: dict[str, dict] = {}


# ─── GET /scenario/types ──────────────────────────────────────────────────────
@router.get("/types", summary="List all Know Your Rights scenarios")
async def list_scenario_types():
    """Returns all available guided scenarios with Urdu/English titles."""
    return {"scenarios": get_scenario_list()}


# ─── POST /scenario/start ─────────────────────────────────────────────────────
@router.post("/start", status_code=status.HTTP_201_CREATED,
             summary="Start a Know Your Rights session")
async def start_scenario(
    payload: StartRequest,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Initialises a new session and returns the first question.
    Each session has a unique UUID used for subsequent answer submissions.
    """
    first_step = get_first_step(payload.scenario_type)
    if not first_step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{payload.scenario_type}' not found. Call /scenario/types to see available scenarios.",
        )

    session_id = str(uuid4())

    # Store session state
    _sessions[session_id] = {
        "scenario_type": payload.scenario_type,
        "language":      payload.language,
        "user_id":       str(payload.user_id) if payload.user_id else None,
        "current_step":  "start",
        "answers_path":  [],
        "started_at":    datetime.utcnow().isoformat(),
        "is_completed":  False,
    }

    logger.info(f"[/scenario/start] New session {session_id[:8]} scenario={payload.scenario_type}")

    return {
        "session_id":   session_id,
        "scenario_type": payload.scenario_type,
        **first_step,
    }


# ─── POST /scenario/{session_id}/answer ──────────────────────────────────────
@router.post("/{session_id}/answer", status_code=status.HTTP_200_OK,
             summary="Submit a yes/no answer and get the next step")
async def answer_step(
    session_id: str,
    payload: AnswerRequest,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Records the user's answer and returns the next step or final guidance.
    When is_terminal=True, action_steps and guidance_ur are populated.
    """
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired. Please start a new session.",
        )

    if session["is_completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session is already completed. Start a new one.",
        )

    # Validate answer
    if payload.answer not in ("yes", "no", "unsure"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Answer must be 'yes', 'no', or 'unsure'.",
        )

    # Record answer in session
    session["answers_path"].append({
        "step_id":   payload.step_id,
        "answer":    payload.answer,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Get next step
    next_step = get_next_step(
        scenario_id=session["scenario_type"],
        current_step_id=payload.step_id,
        answer=payload.answer,
    )

    if not next_step:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not determine next step. Please restart the scenario.",
        )

    # Update session
    session["current_step"] = next_step["step_id"]

    if next_step.get("is_terminal"):
        session["is_completed"] = True
        session["final_guidance"] = next_step.get("guidance_ur", "")

        # Persist to Supabase if user is authenticated
        if session.get("user_id"):
            await _persist_session(db, session_id, session, next_step)

        logger.info(f"[/scenario/answer] Session {session_id[:8]} completed at step {next_step['step_id']}")
    else:
        logger.info(f"[/scenario/answer] Session {session_id[:8]} → step {next_step['step_id']}")

    return {
        "session_id": session_id,
        **next_step,
    }


# ─── GET /scenario/{session_id} ───────────────────────────────────────────────
@router.get("/{session_id}", summary="Get current session state")
async def get_session(session_id: str):
    """Returns the full session including answers path and current step."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired.",
        )

    current = get_step(session["scenario_type"], session["current_step"])

    return {
        "session_id":    session_id,
        "scenario_type": session["scenario_type"],
        "is_completed":  session["is_completed"],
        "answers_path":  session["answers_path"],
        "current_step":  current,
    }


# ─── GET /scenario/types (already defined above) ─────────────────────────────

# ─── Internal persistence ─────────────────────────────────────────────────────
async def _persist_session(
    db: AsyncClient,
    session_id: str,
    session: dict,
    final_step: dict,
) -> None:
    """Saves completed scenario session to Supabase."""
    try:
        await db.table("scenario_sessions").insert({
            "user_id":       session["user_id"],
            "scenario_type": session["scenario_type"],
            "session_language": session["language"],
            "answers_path":  session["answers_path"],
            "final_guidance": final_step.get("guidance_ur", ""),
            "action_steps":  [
                {"step_number": i+1, "action": a, "urgency": final_step.get("urgency", "within_week")}
                for i, a in enumerate(final_step.get("action_steps", []))
            ],
            "emergency_contacts": [
                {"contact": h} for h in final_step.get("helplines", [])
            ],
            "is_completed": True,
        }).execute()
        logger.info(f"[scenario] Persisted session {session_id[:8]}")
    except Exception as exc:
        logger.warning(f"[scenario] Non-fatal persist error: {exc}")
