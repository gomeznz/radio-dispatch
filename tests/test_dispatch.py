"""Lightweight regression checks for the dispatch parser/engine."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from app.dispatch.engine import DispatchEngine
from app.dispatch.protocols import parse_traffic
from app.models import TrafficIn, UnitStatus
from app.storage import DispatchStore


class ProtocolTests(unittest.TestCase):
    def test_available_status(self) -> None:
        parsed = parse_traffic("Dispatch, Unit 12 is 10-8")
        self.assertEqual(parsed.unit_id, "Unit 12")
        self.assertEqual(parsed.status, UnitStatus.AVAILABLE)
        self.assertEqual(parsed.intent, "status_available")

    def test_emergency_fire(self) -> None:
        parsed = parse_traffic(
            "Engine 5 on scene structure fire at Main Street requesting backup"
        )
        self.assertEqual(parsed.unit_id, "Engine 5")
        self.assertEqual(parsed.status, UnitStatus.ONSCENE)
        self.assertEqual(parsed.incident_type, "structure fire")
        self.assertEqual(parsed.priority.value, "emergency")


class EngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DispatchStore(Path(tmp) / "test.db")
            await store.connect()
            engine = DispatchEngine(store)
            reply = await engine.handle_traffic(
                TrafficIn(transcript="Medic 3 transporting Code 3 to General Hospital")
            )
            self.assertIn("Medic 3", reply.response)
            self.assertEqual(reply.intent, "transport")
            logs = await store.list_logs()
            self.assertEqual(len(logs), 1)
            units = await store.list_units()
            self.assertEqual(units[0].unit_id, "Medic 3")


if __name__ == "__main__":
    unittest.main()
