"""Onboarding wizard — 4-step guided setup for new workspaces."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user, get_current_workspace_id
from db.models.onboarding import WorkspaceOnboarding
from db.models.user import User
from db.session import get_db

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class OnboardingProgressOut(BaseModel):
    workspace_id: str
    use_case: Optional[str] = None
    steps: dict[str, bool]
    completed: bool
    progress_percent: int


class StepUpdate(BaseModel):
    step: str
    value: Optional[str] = None


class UseCaseUpdate(BaseModel):
    use_case: str


# ── Helpers ──────────────────────────────────────────────────────────────────

_STEP_FIELDS = [
    "step_choose_use_case",
    "step_connect_model",
    "step_run_demo",
    "step_invite_teammate",
]

_STEP_MAP = {
    "choose_use_case": "step_choose_use_case",
    "connect_model": "step_connect_model",
    "run_demo": "step_run_demo",
    "invite_teammate": "step_invite_teammate",
}


def _to_progress(ob: WorkspaceOnboarding) -> OnboardingProgressOut:
    steps = {
        "choose_use_case": ob.step_choose_use_case,
        "connect_model": ob.step_connect_model,
        "run_demo": ob.step_run_demo,
        "invite_teammate": ob.step_invite_teammate,
    }
    done = sum(1 for v in steps.values() if v)
    return OnboardingProgressOut(
        workspace_id=ob.workspace_id,
        use_case=ob.use_case,
        steps=steps,
        completed=ob.completed,
        progress_percent=int(done / len(steps) * 100),
    )


def _get_or_create(workspace_id: str, user_id: str, db: Session) -> WorkspaceOnboarding:
    ob = db.query(WorkspaceOnboarding).filter(
        WorkspaceOnboarding.workspace_id == workspace_id
    ).first()
    if ob:
        return ob
    ob = WorkspaceOnboarding(workspace_id=workspace_id, user_id=user_id)
    db.add(ob)
    db.commit()
    db.refresh(ob)
    return ob


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/progress", response_model=OnboardingProgressOut)
async def get_onboarding_progress(
    workspace_id: str = Depends(get_current_workspace_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get onboarding progress for the current workspace."""
    ob = _get_or_create(workspace_id, current_user.id, db)
    return _to_progress(ob)


@router.post("/step", response_model=OnboardingProgressOut)
async def complete_step(
    body: StepUpdate,
    workspace_id: str = Depends(get_current_workspace_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark an onboarding step as completed."""
    field = _STEP_MAP.get(body.step)
    if not field:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown step '{body.step}'. Valid: {list(_STEP_MAP.keys())}",
        )

    ob = _get_or_create(workspace_id, current_user.id, db)
    setattr(ob, field, True)

    if body.step == "choose_use_case" and body.value:
        ob.use_case = body.value

    # Check if all steps are done
    all_done = all(getattr(ob, f) for f in _STEP_FIELDS)
    if all_done and not ob.completed:
        ob.completed = True
        ob.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(ob)
    return _to_progress(ob)


@router.post("/use-case", response_model=OnboardingProgressOut)
async def set_use_case(
    body: UseCaseUpdate,
    workspace_id: str = Depends(get_current_workspace_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set use case and mark step 1 as complete."""
    ob = _get_or_create(workspace_id, current_user.id, db)
    ob.use_case = body.use_case
    ob.step_choose_use_case = True

    all_done = all(getattr(ob, f) for f in _STEP_FIELDS)
    if all_done and not ob.completed:
        ob.completed = True
        ob.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(ob)
    return _to_progress(ob)


@router.post("/reset", response_model=OnboardingProgressOut)
async def reset_onboarding(
    workspace_id: str = Depends(get_current_workspace_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reset onboarding progress (admin/debug use)."""
    ob = _get_or_create(workspace_id, current_user.id, db)
    ob.use_case = None
    for f in _STEP_FIELDS:
        setattr(ob, f, False)
    ob.completed = False
    ob.completed_at = None
    db.commit()
    db.refresh(ob)
    return _to_progress(ob)
