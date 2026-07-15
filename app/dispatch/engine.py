"""Core dispatch orchestration."""

from __future__ import annotations

from ..models import DispatchReply, TrafficIn, UnitStatus, utc_now
from ..storage import DispatchStore
from .protocols import parse_traffic
from .responses import craft_response


class DispatchEngine:
    def __init__(self, store: DispatchStore) -> None:
        self.store = store

    async def handle_traffic(self, traffic: TrafficIn) -> DispatchReply:
        parsed = parse_traffic(traffic.transcript)
        crafted = craft_response(parsed)
        now = utc_now()

        if parsed.unit_id and parsed.status:
            await self.store.upsert_unit(
                unit_id=parsed.unit_id,
                status=parsed.status,
                location=parsed.location,
                notes=parsed.incident_type,
                heard_at=now,
            )
        elif parsed.unit_id:
            await self.store.upsert_unit(
                unit_id=parsed.unit_id,
                status=UnitStatus.UNKNOWN,
                location=parsed.location,
                notes=parsed.incident_type,
                heard_at=now,
            )

        log_entry = await self.store.add_log(
            channel=traffic.channel,
            direction="inbound",
            unit_id=parsed.unit_id or traffic.caller,
            transcript=parsed.normalized,
            response=crafted.response,
            intent=parsed.intent,
            priority=parsed.priority,
            incident_type=parsed.incident_type,
            location=parsed.location,
            meta={
                "ten_codes": parsed.ten_codes,
                "spoken_response": crafted.spoken_response,
            },
            timestamp=now,
        )

        return DispatchReply(
            transcript=parsed.normalized,
            response=crafted.response,
            spoken_response=crafted.spoken_response,
            intent=parsed.intent,
            priority=parsed.priority,
            unit_id=parsed.unit_id,
            unit_status=parsed.status,
            incident_type=parsed.incident_type,
            location=parsed.location,
            log_id=log_entry.id,
            timestamp=now,
        )
