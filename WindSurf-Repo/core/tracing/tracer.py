"""Distributed tracing using OpenTelemetry."""

from typing import Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

# Simple tracing implementation (can be replaced with OpenTelemetry later)
# For now, we'll use a lightweight in-memory tracer


class Span:
    """Tracing span."""

    def __init__(
        self,
        trace_id: str,
        span_id: str,
        name: str,
        parent_span_id: Optional[str] = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.name = name
        self.parent_span_id = parent_span_id
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self.status: str = "ok"
        self.status_message: Optional[str] = None

    def set_attribute(self, key: str, value: Any):
        """Set span attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to span."""
        self.events.append(
            {
                "name": name,
                "timestamp": datetime.utcnow().isoformat(),
                "attributes": attributes or {},
            }
        )

    def set_status(self, status: str, message: Optional[str] = None):
        """Set span status."""
        self.status = status
        self.status_message = message

    def finish(self):
        """Finish span."""
        self.end_time = datetime.utcnow()

    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return 0.0


class Tracer:
    """
    Distributed tracer for edge routing and ML operations.

    Tracks spans across edge ↔ central requests.
    Can be replaced with OpenTelemetry implementation later.
    """

    def __init__(self):
        self.spans: Dict[str, Span] = {}  # span_id -> span
        self.traces: Dict[str, List[str]] = {}  # trace_id -> [span_ids]
        self.enabled = True

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        Start a new span.

        Args:
            name: Span name
            trace_id: Optional trace ID (creates new trace if not provided)
            parent_span_id: Optional parent span ID
            attributes: Optional initial attributes

        Returns:
            Span object
        """
        if not self.enabled:
            # Return no-op span if tracing disabled
            return Span("", "", name)

        if trace_id is None:
            trace_id = str(uuid.uuid4())

        span_id = str(uuid.uuid4())

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            name=name,
            parent_span_id=parent_span_id,
        )

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        self.spans[span_id] = span

        # Track in trace
        if trace_id not in self.traces:
            self.traces[trace_id] = []
        self.traces[trace_id].append(span_id)

        return span

    @contextmanager
    def span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for span.

        Usage:
            with tracer.span("edge_routing", attributes={"region": "eu-west"}):
                # Do work
                pass
        """
        span = self.start_span(
            name=name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            attributes=attributes,
        )

        try:
            yield span
            span.set_status("ok")
        except Exception as e:
            span.set_status("error", str(e))
            raise
        finally:
            span.finish()

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace with all spans."""
        if trace_id not in self.traces:
            return None

        span_ids = self.traces[trace_id]
        spans = [self.spans[sid] for sid in span_ids if sid in self.spans]

        return {
            "trace_id": trace_id,
            "spans": [
                {
                    "span_id": span.span_id,
                    "name": span.name,
                    "parent_span_id": span.parent_span_id,
                    "start_time": span.start_time.isoformat(),
                    "end_time": span.end_time.isoformat() if span.end_time else None,
                    "duration_ms": span.duration_ms(),
                    "attributes": span.attributes,
                    "events": span.events,
                    "status": span.status,
                    "status_message": span.status_message,
                }
                for span in spans
            ],
        }

    def inject_trace_context(self, headers: Dict[str, str], trace_id: str, span_id: str):
        """
        Inject trace context into HTTP headers.

        For edge ↔ central communication.
        """
        headers["X-Trace-Id"] = trace_id
        headers["X-Span-Id"] = span_id

    def extract_trace_context(self, headers: Dict[str, str]) -> Optional[tuple[str, str]]:
        """
        Extract trace context from HTTP headers.

        Returns (trace_id, parent_span_id) if found.
        """
        trace_id = headers.get("X-Trace-Id")
        parent_span_id = headers.get("X-Span-Id")

        if trace_id and parent_span_id:
            return (trace_id, parent_span_id)

        return None


# Global tracer
_tracer = Tracer()


def get_tracer() -> Tracer:
    """Get global tracer instance."""
    return _tracer
