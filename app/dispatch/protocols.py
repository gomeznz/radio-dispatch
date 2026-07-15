"""Maritime radio protocol helpers: distress signals, vessel parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..models import Priority, UnitStatus

FILLER_WORDS = {
    "uh",
    "um",
    "er",
    "ah",
    "static",
    "garbled",
    "broken",
    "unintelligible",
    "inaudible",
}

MARITIME_SIGNALS = {
    "mayday": [
        r"\bmay\s*day\s+may\s*day\s+may\s*day\b",
        r"\bmayday\s+mayday\s+mayday\b",
        r"\bmayday\b",
    ],
    "pan_pan": [
        r"\bpan\s+pan\s+pan\b",
        r"\bpan\s+pan\b",
        r"\bpan-pan\b",
    ],
    "securite": [
        r"\bsecurit[ée]?\b",
        r"\bsecuritay\b",
        r"\bsecurity\b",
        r"\bs[eé]curit[eé]\s+s[eé]curit[eé]\s+s[eé]curit[eé]\b",
    ],
}

VESSEL_PATTERNS = [
    re.compile(
        r"\bthis is\s+(?:the\s+)?(.+?)(?:,|\.|over|standing by|calling|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:mv|m/v|f/v|sv|yacht|fishing vessel|motor vessel|sailing vessel|"
        r"pleasure craft|tug|pilot boat)\s+([A-Za-z0-9][\w\s'-]+?)(?:,|\.|over|$)",
        re.IGNORECASE,
    ),
    re.compile(r"\bvessel\s+([A-Za-z0-9][\w\s'-]+?)(?:,|\.|over|$)", re.IGNORECASE),
    re.compile(r"\bcallsign\s+([A-Z0-9]{2,8})\b", re.IGNORECASE),
]

LOCATION_PATTERN = re.compile(
    r"(?:position|located|location|at|off|near|latitude|coordinates?|bearing|"
    r"abreast of|south of|north of|east of|west of)\s+(.+?)(?:,|\.|over|$)",
    re.IGNORECASE,
)

UNINTELLIGIBLE_MARKERS = [
    re.compile(r"\[inaudible\]", re.IGNORECASE),
    re.compile(r"\[unintelligible\]", re.IGNORECASE),
    re.compile(r"^\?+$"),
    re.compile(r"^(static|garbled|broken|unintelligible)\.?$", re.IGNORECASE),
]


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
    replacements = {
        "may day": "mayday",
        "pan pan pan": "pan pan pan",
        "securitay": "securite",
        "security security security": "securite securite securite",
    }
    lowered = cleaned.lower()
    for src, dst in replacements.items():
        lowered = lowered.replace(src, dst)
    return lowered


def _clean_vessel_name(name: str) -> str:
    cleaned = name.strip(" .,'\"")
    cleaned = re.sub(
        r"^(?:the\s+)?(?:mv|m/v|f/v|sv|yacht|fishing vessel|motor vessel|sailing vessel|"
        r"pleasure craft|tug|pilot boat)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.title()


def extract_vessel(text: str) -> Optional[str]:
    for pattern in VESSEL_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        name = _clean_vessel_name(match.group(1))
        if len(name) >= 2:
            return name
    return None


def extract_location(text: str) -> Optional[str]:
    match = LOCATION_PATTERN.search(text)
    if not match:
        return None
    location = match.group(1).strip(" .,")
    location = re.sub(
        r"\b(requesting|please|over|copy|standing by)\b.*$",
        "",
        location,
        flags=re.IGNORECASE,
    )
    location = location.strip(" .,")
    return location or None


def detect_maritime_signal(text: str) -> Optional[str]:
    for signal, patterns in MARITIME_SIGNALS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return signal
    return None


def is_unintelligible(text: str) -> bool:
    normalized = normalize_transcript(text)
    if not normalized:
        return True

    for pattern in UNINTELLIGIBLE_MARKERS:
        if pattern.search(normalized):
            return True

    alpha_chars = re.sub(r"[^a-z]", "", normalized)
    if len(alpha_chars) < 2:
        return True

    words = re.findall(r"[a-z0-9]+", normalized)
    meaningful = [word for word in words if word not in FILLER_WORDS and len(word) > 1]
    if meaningful:
        return False

    return detect_maritime_signal(normalized) is None


def infer_priority(signal: Optional[str]) -> Priority:
    if signal == "mayday":
        return Priority.EMERGENCY
    if signal == "pan_pan":
        return Priority.PRIORITY
    return Priority.ROUTINE


def infer_intent(text: str, signal: Optional[str]) -> str:
    if is_unintelligible(text):
        return "unintelligible"
    if signal == "securite":
        return "securite"
    if signal == "mayday":
        return "mayday"
    if signal == "pan_pan":
        return "pan_pan"
    if re.search(r"\b(repeat|say again|come again)\b", text, re.IGNORECASE):
        return "repeat_request"
    if re.search(r"\b(position|location|coordinates?|latitude)\b", text, re.IGNORECASE):
        return "position_request"
    if re.search(r"\bradio check\b", text, re.IGNORECASE):
        return "radio_check"
    return "general_traffic"


def infer_vessel_status(signal: Optional[str], intent: str) -> Optional[UnitStatus]:
    if intent == "mayday":
        return UnitStatus.BUSY
    if intent == "pan_pan":
        return UnitStatus.ENROUTE
    if signal == "securite":
        return UnitStatus.UNKNOWN
    return None


def parse_traffic(transcript: str) -> ParsedTraffic:
    normalized = normalize_transcript(transcript)
    signal = detect_maritime_signal(normalized)
    intent = infer_intent(transcript, signal)
    unit_id = extract_vessel(normalized)
    location = extract_location(normalized)
    priority = infer_priority(signal)
    status = infer_vessel_status(signal, intent)
    incident_type = signal

    return ParsedTraffic(
        normalized=normalized,
        unit_id=unit_id,
        ten_codes=[],
        status=status,
        incident_type=incident_type,
        location=location,
        priority=priority,
        intent=intent,
    )
