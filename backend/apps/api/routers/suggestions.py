"""Suggestions endpoints - optimization suggestions."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.autonomous.suggestions.optimizer import get_optimization_suggestions
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/suggestions", tags=["suggestions"])
optimization_suggestions = get_optimization_suggestions()


class Suggestion(BaseModel):
    """Optimization suggestion."""
    type: str
    title: str
    description: str
    impact: str  # low, medium, high
    effort: str  # low, medium, high
    priority: float
    action: str


class SuggestionsResponse(BaseModel):
    """Suggestions response."""
    suggestions: List[Suggestion]
    count: int


@router.get("", response_model=SuggestionsResponse)
async def get_suggestions(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """
    Get optimization suggestions for workspace.
    
    Returns proactive suggestions that save money or improve performance.
    """
    suggestions = optimization_suggestions.generate_suggestions(
        workspace_id=workspace_id,
        db=db,
    )
    
    return SuggestionsResponse(
        suggestions=[
            Suggestion(
                type=s["type"],
                title=s["title"],
                description=s["description"],
                impact=s["impact"],
                effort=s["effort"],
                priority=s["priority"],
                action=s["action"],
            )
            for s in suggestions
        ],
        count=len(suggestions),
    )


@router.get("/summary")
async def get_suggestions_summary(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """
    Get suggestions summary.
    
    Returns count by type and impact.
    """
    suggestions = optimization_suggestions.generate_suggestions(
        workspace_id=workspace_id,
        db=db,
    )
    
    # Group by type
    by_type = {}
    by_impact = {"low": 0, "medium": 0, "high": 0}
    
    for s in suggestions:
        suggestion_type = s["type"]
        if suggestion_type not in by_type:
            by_type[suggestion_type] = 0
        by_type[suggestion_type] += 1
        
        impact = s["impact"]
        if impact in by_impact:
            by_impact[impact] += 1
    
    return {
        "total": len(suggestions),
        "by_type": by_type,
        "by_impact": by_impact,
    }
