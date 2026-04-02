"""AI quality scoring."""
from typing import Dict, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QualityScore(BaseModel):
    """Quality score result."""

    overall_score: float  # 0-1
    relevance: float  # 0-1
    accuracy: float  # 0-1
    coherence: float  # 0-1
    completeness: float  # 0-1
    metadata: Dict[str, any]


class QualityScorer:
    """Score AI outputs for quality."""

    def score_output(
        self,
        input_text: str,
        output_text: str,
        operation_type: str,
    ) -> QualityScore:
        """
        Score AI output quality.
        
        Returns quality scores for different dimensions.
        """
        # Basic scoring (can be enhanced with ML models)
        # For now, use heuristics
        
        # Relevance: Check if output relates to input
        relevance = self._score_relevance(input_text, output_text)
        
        # Accuracy: Check for factual errors (basic - can use fact-checking APIs)
        accuracy = 0.85  # Default, can be enhanced
        
        # Coherence: Check if output is coherent
        coherence = self._score_coherence(output_text)
        
        # Completeness: Check if output is complete
        completeness = self._score_completeness(output_text, operation_type)
        
        # Overall score (weighted average)
        overall_score = (
            relevance * 0.3 +
            accuracy * 0.3 +
            coherence * 0.2 +
            completeness * 0.2
        )
        
        return QualityScore(
            overall_score=overall_score,
            relevance=relevance,
            accuracy=accuracy,
            coherence=coherence,
            completeness=completeness,
            metadata={
                "scored_at": datetime.utcnow().isoformat(),
                "operation_type": operation_type,
            },
        )

    def _score_relevance(self, input_text: str, output_text: str) -> float:
        """Score relevance (basic keyword overlap)."""
        input_words = set(input_text.lower().split())
        output_words = set(output_text.lower().split())
        
        if not input_words:
            return 1.0
        
        overlap = len(input_words & output_words)
        relevance = min(overlap / len(input_words), 1.0)
        return relevance

    def _score_coherence(self, text: str) -> float:
        """Score coherence (basic - check sentence structure)."""
        sentences = text.split(".")
        if len(sentences) < 2:
            return 0.8  # Single sentence, assume coherent
        
        # Check average sentence length (very basic heuristic)
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        # Sentences between 5-20 words are typically coherent
        if 5 <= avg_length <= 20:
            return 0.9
        elif 3 <= avg_length < 5 or 20 < avg_length <= 30:
            return 0.7
        else:
            return 0.5

    def _score_completeness(self, text: str, operation_type: str) -> float:
        """Score completeness based on operation type."""
        if operation_type == "transcribe":
            # Transcription should be substantial
            return 0.9 if len(text) > 50 else 0.5
        elif operation_type == "extract":
            # Extraction should have structured output
            return 0.8 if ":" in text or "\n" in text else 0.6
        else:
            return 0.8  # Default


# Global quality scorer
_quality_scorer = QualityScorer()


def get_quality_scorer() -> QualityScorer:
    """Get quality scorer."""
    return _quality_scorer
