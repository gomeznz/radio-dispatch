"""Regression checks for maritime dispatch parsing and responses."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.dispatch.engine import DispatchEngine
from app.dispatch.protocols import parse_traffic
from app.dispatch.responses import craft_response
from app.models import Priority, TrafficIn, UnitStatus
from app.storage import DispatchStore


class ProtocolTests(unittest.TestCase):
    def test_mayday_distress(self) -> None:
        parsed = parse_traffic(
            "Mayday Mayday Mayday, this is fishing vessel Blue Horizon, "
            "engine failure, position off Cape Reinga"
        )
        self.assertEqual(parsed.intent, "mayday")
        self.assertEqual(parsed.priority, Priority.EMERGENCY)
        self.assertEqual(parsed.incident_type, "mayday")
        self.assertEqual(parsed.unit_id, "Blue Horizon")

    def test_pan_pan_urgent(self) -> None:
        parsed = parse_traffic(
            "Pan Pan Pan, this is yacht Serenity, disabled and drifting near harbour entrance"
        )
        self.assertEqual(parsed.intent, "pan_pan")
        self.assertEqual(parsed.priority, Priority.PRIORITY)
        self.assertEqual(parsed.status, UnitStatus.ENROUTE)

    def test_securite_no_response_intent(self) -> None:
        parsed = parse_traffic(
            "Securitay Securitay Securitay, navigation hazard reported in the main channel"
        )
        self.assertEqual(parsed.intent, "securite")
        self.assertEqual(parsed.priority, Priority.ROUTINE)

    def test_unintelligible(self) -> None:
        parsed = parse_traffic("[unintelligible]")
        self.assertEqual(parsed.intent, "unintelligible")

    def test_unintelligible_reply(self) -> None:
        crafted = craft_response(parse_traffic("static"))
        self.assertEqual(crafted.response, "Vessel calling, please repeat.")

    def test_bluff_departing(self) -> None:
        parsed = parse_traffic(
            "Bluff Fishermans Radio, this is fishing vessel Southern Cross, departing Bluff harbour"
        )
        self.assertEqual(parsed.intent, "bluff_departing")
        self.assertEqual(parsed.unit_id, "Southern Cross")
        self.assertEqual(parsed.status, UnitStatus.ENROUTE)

    def test_bluff_returning(self) -> None:
        parsed = parse_traffic(
            "This is FV Ocean Star, Bluff Fishermans Radio, back in port"
        )
        self.assertEqual(parsed.intent, "bluff_returning")
        self.assertEqual(parsed.unit_id, "Ocean Star")
        self.assertEqual(parsed.status, UnitStatus.AVAILABLE)


class ResponseTests(unittest.TestCase):
    def test_securite_has_no_spoken_reply(self) -> None:
        crafted = craft_response(parse_traffic("Securite, submerged log near marker 12"))
        self.assertEqual(crafted.spoken_response, "")
        self.assertIn("no response", crafted.response.lower())

    def test_mayday_reply(self) -> None:
        crafted = craft_response(
            parse_traffic("Mayday, this is MV Atlantic, taking on water")
        )
        self.assertIn("Mayday received", crafted.response)
        self.assertIn("Distress acknowledged", crafted.response)

    def test_bluff_departing_asks_pob(self) -> None:
        crafted = craft_response(
            parse_traffic(
                "Bluff Fisherman's Radio, this is Southern Cross, departing port"
            )
        )
        self.assertIn("Bluff Fishermans Radio", crafted.response)
        self.assertIn("number of persons on board", crafted.response.lower())

    def test_bluff_returning_acknowledged(self) -> None:
        crafted = craft_response(
            parse_traffic("This is Ocean Star, Bluff Fishermans Radio, returning to port")
        )
        self.assertIn("Bluff Fishermans Radio", crafted.response)
        self.assertIn("Welcome back", crafted.response)


class EngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_pan_pan_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DispatchStore(Path(tmp) / "test.db")
            await store.connect()
            engine = DispatchEngine(store)
            reply = await engine.handle_traffic(
                TrafficIn(
                    transcript=(
                        "Pan Pan Pan, this is yacht Serenity, "
                        "requesting tow at harbour entrance"
                    )
                )
            )
            self.assertEqual(reply.intent, "pan_pan")
            self.assertIn("Pan Pan received", reply.response)
            logs = await store.list_logs()
            self.assertEqual(len(logs), 1)
            units = await store.list_units()
            self.assertEqual(units[0].unit_id, "Serenity")

    async def test_securite_logs_without_voice_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DispatchStore(Path(tmp) / "test.db")
            await store.connect()
            engine = DispatchEngine(store)
            reply = await engine.handle_traffic(
                TrafficIn(transcript="Securitay, dredging operations in progress")
            )
            self.assertEqual(reply.intent, "securite")
            self.assertEqual(reply.spoken_response, "")
            logs = await store.list_logs()
            self.assertEqual(len(logs), 1)


if __name__ == "__main__":
    unittest.main()
