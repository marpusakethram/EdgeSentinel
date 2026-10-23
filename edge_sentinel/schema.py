"""The bounded, strict JSON Lines wire contract."""

import json
import math
from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEVICES = ("press-01", "conveyor-02", "cooling-03")
MAX_MESSAGE_BYTES = 4096


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    device_id: Literal["press-01", "conveyor-02", "cooling-03"]
    timestamp: str
    event_type: Literal["heartbeat", "telemetry", "connection_failure", "control_write"]
    temperature: float = Field(ge=-100, le=500)
    vibration: float = Field(ge=0, le=100)
    status: Literal["ok", "warning", "failed"]
    source_ip: str
    details: str = Field(max_length=512)

    @field_validator("timestamp")
    @classmethod
    def valid_timestamp(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return parsed.astimezone(timezone.utc).isoformat()

    @field_validator("source_ip")
    @classmethod
    def valid_ip(cls, value: str) -> str:
        return str(IPv4Address(value))

    @field_validator("temperature", "vibration")
    @classmethod
    def finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("numbers must be finite")
        return value


def parse_message(raw: bytes) -> Message:
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("message exceeds 4096 bytes including newline")
    return Message.model_validate(json.loads(raw))
