"""Build spoken and logged dispatcher replies from parsed radio traffic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..models import Priority, UnitStatus
from .protocols import ParsedTraffic


@dataclass
class CraftedResponse:
    response: str
    spoken_response: str


def _unit_label(parsed: ParsedTraffic) -> str:
    return parsed.unit_id or "Unit"


def craft_response(parsed: ParsedTraffic) -> CraftedResponse:
    unit = _unit_label(parsed)
    location = parsed.location
    incident = parsed.incident_type

    if parsed.intent == "repeat_request":
        text = f"Dispatch copy, {unit}. Say again your last traffic."
    elif parsed.intent == "location_request":
        if location:
            text = f"Dispatch copy, {unit}. Your 10-20 is logged as {location}."
        else:
            text = f"Dispatch to {unit}, advise your 10-20."
    elif parsed.intent == "on_scene":
        scene = f" at {location}" if location else ""
        detail = f" {incident.replace('_', ' ')}" if incident else ""
        text = f"Dispatch copy, {unit} on scene{scene}.{detail} Stand by for further."
    elif parsed.intent == "transport":
        destination = f" to {location}" if location else ""
        code = " Code 3" if parsed.priority == Priority.EMERGENCY else ""
        text = f"Dispatch copy, {unit} transporting{destination}{code}. Advise ETA when able."
    elif parsed.intent == "status_available":
        text = f"Dispatch copy, {unit} 10-8 available."
    elif parsed.intent == "status_oos":
        text = f"Dispatch copy, {unit} 10-7 out of service."
    elif parsed.intent == "enroute":
        target = f" to {location}" if location else ""
        text = f"Dispatch copy, {unit} en route{target}. Keep us advised."
    elif parsed.intent == "resource_request":
        need = incident or "additional resources"
        where = f" at {location}" if location else ""
        text = (
            f"Dispatch copy, {unit} requesting {need}{where}. "
            "Air cover remaining units and advise."
        )
    elif parsed.intent == "incident_report":
        kind = incident or "incident"
        where = f" at {location}" if location else ""
        if parsed.priority == Priority.EMERGENCY:
            text = (
                f"Dispatch copies emergency traffic from {unit}, {kind}{where}. "
                "All units stand by."
            )
        else:
            text = f"Dispatch copy, {unit}, {kind}{where} is logged."
    elif parsed.intent == "radio_check":
        text = f"Dispatch to {unit}, loud and clear."
    else:
        ack = f", {unit}" if parsed.unit_id else ""
        text = f"Dispatch copy{ack}. Your traffic is logged."

    spoken = _to_spoken(text)
    return CraftedResponse(response=text, spoken_response=spoken)


def status_phrase(status: Optional[UnitStatus]) -> str:
    mapping = {
        UnitStatus.AVAILABLE: "available",
        UnitStatus.ENROUTE: "en route",
        UnitStatus.ONSCENE: "on scene",
        UnitStatus.BUSY: "busy",
        UnitStatus.TRANSPORTING: "transporting",
        UnitStatus.OUT_OF_SERVICE: "out of service",
        UnitStatus.UNKNOWN: "unknown",
    }
    return mapping.get(status or UnitStatus.UNKNOWN, "unknown")


def _to_spoken(text: str) -> str:
    spoken = text
    replacements = {
        "10-8": "ten eight",
        "10-7": "ten seven",
        "10-4": "ten four",
        "10-20": "ten twenty",
        "10-9": "ten nine",
        "10-23": "ten twenty three",
        "ETA": "E T A",
        "Code 3": "code three",
        "Code 2": "code two",
    }
    for src, dst in replacements.items():
        spoken = spoken.replace(src, dst)
    return spoken
