"""Build maritime coast-station replies from parsed radio traffic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..models import Priority, UnitStatus
from .protocols import ParsedTraffic


@dataclass
class CraftedResponse:
    response: str
    spoken_response: str


def _vessel_label(parsed: ParsedTraffic) -> str:
    return parsed.unit_id or "vessel"


def craft_response(parsed: ParsedTraffic) -> CraftedResponse:
    vessel = _vessel_label(parsed)
    location = parsed.location

    if parsed.intent == "unintelligible":
        text = "Vessel calling, please repeat."
    elif parsed.intent == "securite":
        return CraftedResponse(
            response="(no response — sécurité broadcast)",
            spoken_response="",
        )
    elif parsed.intent == "mayday":
        where = f" Position noted as {location}." if location else ""
        text = (
            f"Mayday received. {vessel.title()}, this is Coast Radio. "
            f"Distress acknowledged.{where} Stand by, assistance is being coordinated."
        )
    elif parsed.intent == "pan_pan":
        where = f" Position noted as {location}." if location else ""
        text = (
            f"Pan Pan received. {vessel.title()}, this is Coast Radio. "
            f"Urgent traffic acknowledged.{where} "
            "Please state nature of urgency and number of persons on board."
        )
    elif parsed.intent == "repeat_request":
        text = "Vessel calling, please repeat."
    elif parsed.intent == "position_request":
        if location:
            text = (
                f"{vessel.title()}, this is Coast Radio. "
                f"Your position is logged as {location}."
            )
        else:
            text = (
                f"{vessel.title()}, this is Coast Radio. "
                "Please advise your position."
            )
    elif parsed.intent == "radio_check":
        text = f"{vessel.title()}, this is Coast Radio. You are readable, strength 5."
    else:
        ack = f"{vessel.title()}, " if parsed.unit_id else ""
        text = f"{ack}this is Coast Radio. Received, your message is logged."

    spoken = _to_spoken(text)
    return CraftedResponse(response=text, spoken_response=spoken)


def status_phrase(status: Optional[UnitStatus]) -> str:
    mapping = {
        UnitStatus.AVAILABLE: "available",
        UnitStatus.ENROUTE: "urgent traffic",
        UnitStatus.ONSCENE: "on scene",
        UnitStatus.BUSY: "distress",
        UnitStatus.TRANSPORTING: "underway",
        UnitStatus.OUT_OF_SERVICE: "out of service",
        UnitStatus.UNKNOWN: "unknown",
    }
    return mapping.get(status or UnitStatus.UNKNOWN, "unknown")


def _to_spoken(text: str) -> str:
    spoken = text
    replacements = {
        "Pan Pan": "pan pan",
        "Mayday": "mayday",
        "sécurité": "securitay",
        "Coast Radio": "Coast Radio",
    }
    for src, dst in replacements.items():
        spoken = spoken.replace(src, dst)
    return spoken
