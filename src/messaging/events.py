from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class MessageEnvelope:
    event_name: str
    payload: dict[str, str]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
