"""Radio protocol helpers: 10-codes, unit parsing, incident keywords."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..models import Priority, UnitStatus

TEN_CODES = {
    "10-4": "acknowledged",
    "10-6": "busy",
    "10-7": "out of service",
    "10-8": "in service",
    "10-9": "repeat",
    "10-20": "location",
    "10-23": "arrived on scene",
    "10-97": "arrived",
    "10-98": "assignment complete",
}

STATUS_PHRASES = {
    UnitStatus.AVAILABLE: [
        r"\b10-8\b",
        r"\bin service\b",
        r"\bavailable\b",
        r"\bclear(?:ing)?\b",
        r"\breturning to station\b",
    ],
    UnitStatus.ENROUTE: [
        r"\ben\s*route\b",
        r"\bresponding\b",
        r"\bcode\s*[123]\b",
        r"\brolling\b",
    ],
    UnitStatus.ONSCENE: [
        r"\bon\s*scene\b",
        r"\b10-23\b",
        r"\b10-97\b",
        r"\barrived\b",
    ],
    UnitStatus.TRANSPORTING: [
        r"\btransport(?:ing)?\b",
        r"\ben\s*route to (?:hospital|clinic|er)\b",
    ],
    UnitStatus.OUT_OF_SERVICE: [
        r"\b10-7\b",
        r"\bout of service\b",
        r"\boff duty\b",
    ],
    UnitStatus.BUSY: [
        r"\b10-6\b",
        r"\bbusy\b",
        r"\btraffic stop\b",
        r"\binvestigating\b",
    ],
}

INCIDENT_KEYWORDS = {
    "structure fire": ["structure fire", "building fire", "house fire"],
    "medical": ["medical", "patient", "cpr", "chest pain", "breathing"],
    "traffic": ["traffic stop", "vehicle accident", "mvc", "crash", "collision"],
    "backup": ["backup", "additional units", "assistance", "help"],
    "welfare": ["welfare check", "wellness check"],
    "alarm": ["alarm", "fire alarm"],
}

UNIT_PATTERN = re.compile(
    r"\b("
    r"(?:unit|engine|medic|ambulance|ladder|truck|squad|rescue|battalion|chief|car|pd)"
    r"\s*\d{1,3}"
    r")\b",
    re.IGNORECASE,
)

LOCATION_PATTERN = re.compile(
    r"(?:\bat|on|near|location(?: is)?|10-20(?: is)?)\s+(.+?)(?:,|\.|$)",
    re.IGNORECASE,
)


@dataclass
class ParsedTraffic:
    normalized: str
    unit_id: Optional[str]
    ten_codes: list[str]
    status: Optional[UnitStatus]
    incident_type: Optional[str]
    location: Optional[str]
    priority: Priority
    intent: str


def normalize_transcript(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    cleaned = cleaned.replace("ten four", "10-4")
    cleaned = cleaned.replace("ten 4", "10-4")
    cleaned = re.sub(r"\bten[-\s]?(\d{1,2})\b", r"10-\1", cleaned, flags=re.IGNORECASE)
    return cleaned


def extract_unit(text: str) -> Optional[str]:
    match = UNIT_PATTERN.search(text)
    if not match:
        return None
    raw = match.group(1)
    parts = raw.split()
    if len(parts) == 1:
        return raw.upper()
    kind, number = parts[0], parts[1]
    return f"{kind.title()} {number}"


def extract_location(text: str) -> Optional[str]:
    match = LOCATION_PATTERN.search(text)
    if not match:
        return None
    location = match.group(1).strip(" .,")
    location = re.sub(r"\b(requesting|please|over|copy)\b.*$", "", location, flags=re.IGNORECASE)
    location = location.strip(" .,")
    return location or None


def detect_status(text: str) -> Optional[UnitStatus]:
    # Prefer specific statuses first so phrases like "transporting Code 3"
    # are not classified as generic enroute traffic.
    priority_order = [
        UnitStatus.TRANSPORTING,
        UnitStatus.ONSCENE,
        UnitStatus.OUT_OF_SERVICE,
        UnitStatus.AVAILABLE,
        UnitStatus.BUSY,
        UnitStatus.ENROUTE,
    ]
    for status in priority_order:
        for pattern in STATUS_PHRASES.get(status, []):
            if re.search(pattern, text, re.IGNORECASE):
                return status
    return None


def detect_incident(text: str) -> Optional[str]:
    lowered = text.lower()
    for label, keywords in INCIDENT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return label
    return None


def detect_ten_codes(text: str) -> list[str]:
    found: list[str] = []
    for code in TEN_CODES:
        if re.search(rf"\b{re.escape(code)}\b", text, re.IGNORECASE):
            found.append(code)
    return found


def infer_priority(text: str, incident: Optional[str], status: Optional[UnitStatus]) -> Priority:
    lowered = text.lower()
    if any(token in lowered for token in ("emergency", "code 3", "shots fired", "officer down", "structure fire")):
        return Priority.EMERGENCY
    if incident in {"structure fire", "medical", "backup"} or status == UnitStatus.TRANSPORTING:
        return Priority.PRIORITY
    if "code 2" in lowered or "priority" in lowered:
        return Priority.PRIORITY
    return Priority.ROUTINE


def infer_intent(
    text: str,
    status: Optional[UnitStatus],
    incident: Optional[str],
    ten_codes: list[str],
) -> str:
    lowered = text.lower()
    if "10-9" in ten_codes or "repeat" in lowered or "say again" in lowered:
        return "repeat_request"
    if "10-20" in ten_codes or "location" in lowered:
        return "location_request"
    if status == UnitStatus.ONSCENE:
        return "on_scene"
    if status == UnitStatus.TRANSPORTING:
        return "transport"
    if status == UnitStatus.AVAILABLE:
        return "status_available"
    if status == UnitStatus.OUT_OF_SERVICE:
        return "status_oos"
    if status == UnitStatus.ENROUTE:
        return "enroute"
    if incident == "backup" or "requesting" in lowered:
        return "resource_request"
    if incident:
        return "incident_report"
    if "dispatch" in lowered and status is None and incident is None:
        return "general_call"
    return "radio_check" if "radio check" in lowered else "general_traffic"


def parse_traffic(transcript: str) -> ParsedTraffic:
    normalized = normalize_transcript(transcript)
    unit_id = extract_unit(normalized)
    ten_codes = detect_ten_codes(normalized)
    status = detect_status(normalized)
    incident_type = detect_incident(normalized)
    location = extract_location(normalized)
    priority = infer_priority(normalized, incident_type, status)
    intent = infer_intent(normalized, status, incident_type, ten_codes)
    return ParsedTraffic(
        normalized=normalized,
        unit_id=unit_id,
        ten_codes=ten_codes,
        status=status,
        incident_type=incident_type,
        location=location,
        priority=priority,
        intent=intent,
    )
