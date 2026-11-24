"""Comprehensive Test Suite for Smart College Event Planning Assistant.

Validates all 10 project specification features and the test plan in Section 12.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from web.planner import EventPlanner


class TestSmartEventPlanner(unittest.TestCase):
    """Test case suite covering all core algorithms, MFCS concepts, and features."""

    def setUp(self):
        """Create a temporary directory and an isolated EventPlanner instance."""
        self.test_dir = tempfile.mkdtemp()
        self.data_file = Path(self.test_dir) / "test_events.json"
        self.planner = EventPlanner(self.data_file)

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Feature 1: Event Details Management
    # -------------------------------------------------------------------------
    def test_add_and_list_event(self):
        """Test adding valid events and listing them."""
        result = self.planner.add_event({
            "event_id": "EVT100",
            "event_name": "Maths Workshop",
            "date": "2026-12-05",
            "venue": "Hall A",
            "participants": "S001, S002",
            "preferred_window": "09:00-13:00",
            "description": "Discrete Maths",
        })
        success, msg = result[0], result[1]
        self.assertTrue(success, msg)
        self.assertEqual(len(self.planner.events), 1)

        event = self.planner.get_event("EVT100")
        self.assertIsNotNone(event)
        self.assertEqual(event["event_name"], "Maths Workshop")
        self.assertEqual(event["participants"], ["S001", "S002"])
        self.assertEqual(event["preferred_window"], "09:00-13:00")
        self.assertEqual(event["status"], "Unassigned")

    def test_add_event_validation_errors(self):
        """Test validation rules when adding events."""
        # Missing required fields
        success, msg = self.planner.add_event({"event_id": "EVT1"})[:2]
        self.assertFalse(success)

        # Invalid date format
        success, msg = self.planner.add_event({
            "event_id": "EVT1",
            "event_name": "Test",
            "date": "05-12-2026",
            "venue": "Lab 1",
        })[:2]
        self.assertFalse(success)

        # Start time without end time
        success, msg = self.planner.add_event({
            "event_id": "EVT1",
            "event_name": "Test",
            "date": "2026-12-05",
            "venue": "Lab 1",
            "start_time": "10:00",
        })[:2]
        self.assertFalse(success)

        # End time before start time
        success, msg = self.planner.add_event({
            "event_id": "EVT1",
            "event_name": "Test",
            "date": "2026-12-05",
            "venue": "Lab 1",
            "start_time": "12:00",
            "end_time": "11:00",
        })[:2]
        self.assertFalse(success)

        # Duplicate ID — now silently reassigns a new ID, so success=True
        self.planner.add_event({
            "event_id": "EVT1",
            "event_name": "First",
            "date": "2026-12-05",
            "venue": "Lab 1",
        })
        success, msg = self.planner.add_event({
            "event_id": "EVT1",
            "event_name": "Second",
            "date": "2026-12-05",
            "venue": "Lab 2",
        })[:2]
        self.assertTrue(success)  # duplicate ID → auto-reassigned, event added

    def test_update_and_delete_event(self):
        """Test updating fields and deleting an event."""
        self.planner.add_event({
            "event_id": "EVT01",
            "event_name": "Original Name",
            "date": "2026-12-05",
            "venue": "Lab 1",
        })
        success, msg, warnings = self.planner.update_event("EVT01", {
            "event_name": "Updated Name",
            "venue": "Lab 2",
            "start_time": "10:00",
            "end_time": "11:00",
        })
        self.assertTrue(success)
        event = self.planner.get_event("EVT01")
        self.assertEqual(event["event_name"], "Updated Name")
        self.assertEqual(event["venue"], "Lab 2")
        self.assertEqual(event["status"], "Scheduled")

        del_success, del_msg = self.planner.delete_event("EVT01")
        self.assertTrue(del_success)
        self.assertIsNone(self.planner.get_event("EVT01"))

    # -------------------------------------------------------------------------
    # Feature 2: Automatic Conflict Detection (Section 12 Tests 1, 2, 3)
    # -------------------------------------------------------------------------
    def test_shared_participant_overlapping_times(self):
        """Section 12 Test 1: A={S1,S2}, B={S2,S3}, times overlap -> report clash and show S2."""
        self.planner.add_event({
            "event_id": "A",
            "event_name": "Event A",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "10:00",
            "end_time": "11:00",
            "participants": "S1, S2",
        })
        self.planner.add_event({
            "event_id": "B",
            "event_name": "Event B",
            "date": "2026-12-05",
            "venue": "Room 2",
            "start_time": "10:30",
            "end_time": "11:30",
            "participants": "S2, S3",
        })

        conflicts = self.planner.find_conflicts()
        self.assertEqual(len(conflicts["simultaneous_clashes"]), 1)
        clash = conflicts["simultaneous_clashes"][0]
        self.assertIn("S2", clash["shared_participants"])
        self.assertNotIn("S1", clash["shared_participants"])

    def test_no_shared_participant_overlapping_times(self):
        """Section 12 Test 2: A={S1}, B={S2}, times overlap -> No participant clash."""
        self.planner.add_event({
            "event_id": "A",
            "event_name": "Event A",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "10:00",
            "end_time": "11:00",
            "participants": "S1",
        })
        self.planner.add_event({
            "event_id": "B",
            "event_name": "Event B",
            "date": "2026-12-05",
            "venue": "Room 2",
            "start_time": "10:30",
            "end_time": "11:30",
            "participants": "S2",
        })

        conflicts = self.planner.find_conflicts()
        self.assertEqual(len(conflicts["simultaneous_clashes"]), 0)

    def test_shared_participant_different_times(self):
        """Section 12 Test 3: Same student in two events at different times -> No simultaneous clash."""
        self.planner.add_event({
            "event_id": "A",
            "event_name": "Event A",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "09:00",
            "end_time": "10:00",
            "participants": "S1, S2",
        })
        self.planner.add_event({
            "event_id": "B",
            "event_name": "Event B",
            "date": "2026-12-05",
            "venue": "Room 2",
            "start_time": "11:00",
            "end_time": "12:00",
            "participants": "S2, S3",
        })

        conflicts = self.planner.find_conflicts()
        self.assertEqual(len(conflicts["simultaneous_clashes"]), 0)
        # But should show up in conflict graph potential connections for scheduling
        self.assertEqual(len(conflicts["potential_conflicts"]), 1)

    # -------------------------------------------------------------------------
    # Feature 3: Smart Event Priority Ranking (Section 6.2)
    # -------------------------------------------------------------------------
    def test_priority_ranking_degrees_and_tie_breaking(self):
        """Test conflict degree calculation and tie-breaking by participant count then ID."""
        # A connects to B and C (degree 2)
        # B connects to A (degree 1), 3 participants
        # C connects to A (degree 1), 2 participants
        self.planner.add_event({
            "event_id": "A",
            "event_name": "Alpha",
            "date": "2026-12-05",
            "venue": "Room 1",
            "participants": "S1, S2",
        })
        self.planner.add_event({
            "event_id": "B",
            "event_name": "Beta",
            "date": "2026-12-05",
            "venue": "Room 2",
            "participants": "S1, S3, S4",
        })
        self.planner.add_event({
            "event_id": "C",
            "event_name": "Gamma",
            "date": "2026-12-05",
            "venue": "Room 3",
            "participants": "S2, S5",
        })

        ranking = self.planner.get_priority_ranking()
        self.assertEqual(ranking[0]["event_id"], "A")
        self.assertEqual(ranking[0]["conflict_degree"], 2)

        # B and C have degree 1, but B has 3 participants while C has 2
        self.assertEqual(ranking[1]["event_id"], "B")
        self.assertEqual(ranking[1]["conflict_degree"], 1)
        self.assertEqual(ranking[1]["participant_count"], 3)

        self.assertEqual(ranking[2]["event_id"], "C")
        self.assertEqual(ranking[2]["conflict_degree"], 1)
        self.assertEqual(ranking[2]["participant_count"], 2)

    # -------------------------------------------------------------------------
    # Feature 4: Automatic Timetable Generation (Greedy Graph Coloring)
    # -------------------------------------------------------------------------
    def test_graph_coloring_auto_schedule(self):
        """Section 12 Test 7: Connected events receive different slots."""
        self.planner.load_sample_events()
        res = self.planner.create_schedule()
        self.assertEqual(res["scheduled"], 4)
        self.assertEqual(res["unassigned"], 0)

        # EVT001 (Lab 2, S101,S102,S103) connects to EVT002 (Hall 1, S102) and EVT003 (Lab 2, S103)
        evt1 = self.planner.get_event("EVT001")
        evt2 = self.planner.get_event("EVT002")
        evt3 = self.planner.get_event("EVT003")

        # They must not have overlapping slots
        self.assertFalse(self.planner.events_overlap(evt1, evt2))
        self.assertFalse(self.planner.events_overlap(evt1, evt3))

        # EVT001 and EVT003 share Lab 2, so they must also respect the 30-min buffer
        self.assertFalse(self.planner.slots_are_too_close(
            (evt1["start_time"], evt1["end_time"]),
            (evt3["start_time"], evt3["end_time"]),
        ))

    def test_greedy_schedule_preferred_window_constraint(self):
        """Test that automatic scheduler respects preferred time window."""
        self.planner.add_event({
            "event_id": "W1",
            "event_name": "Morning Session",
            "date": "2026-12-05",
            "venue": "Hall A",
            "participants": "S1",
            "preferred_window": "14:00-16:00",
        })
        self.planner.create_schedule()
        w1 = self.planner.get_event("W1")
        self.assertEqual(w1["status"], "Scheduled")
        self.assertEqual(w1["start_time"], "14:00")
        self.assertEqual(w1["end_time"], "15:00")

    def test_unassigned_when_no_valid_slot(self):
        """Section 12 Test 9: When all candidate slots violate constraints, leave unassigned with explanation."""
        # Schedule events filling all slots in Room 1 from 09:00 to 18:00
        for idx, (st, et) in enumerate(self.planner.TIME_SLOTS):
            self.planner.add_event({
                "event_id": f"FILL{idx}",
                "event_name": f"Event {idx}",
                "date": "2026-12-05",
                "venue": "SingleRoom",
                "start_time": st,
                "end_time": et,
                "participants": f"P{idx}",
            })

        # Add a new unassigned event requiring SingleRoom on the same date
        self.planner.add_event({
            "event_id": "BLOCKED",
            "event_name": "Blocked Event",
            "date": "2026-12-05",
            "venue": "SingleRoom",
            "participants": "P_NEW",
        })

        res = self.planner.create_schedule()
        blocked = self.planner.get_event("BLOCKED")
        self.assertEqual(blocked["status"], "Unassigned")
        self.assertIn("BLOCKED", res["unassigned_explanations"])
        self.assertIn("violat", res["unassigned_explanations"]["BLOCKED"]["reason"].lower())

    # -------------------------------------------------------------------------
    # Feature 5: CSV Timetable Export
    # -------------------------------------------------------------------------
    def test_csv_export_format(self):
        """Section 12 Test 10: Validated timetable export with required fields."""
        self.planner.load_sample_events()
        self.planner.create_schedule()
        csv_data = self.planner.export_csv_data()

        lines = [line.strip() for line in csv_data.strip().split("\n") if line.strip()]
        header = lines[0].split(",")
        self.assertIn("Event ID", header)
        self.assertIn("Event Name", header)
        self.assertIn("Date", header)
        self.assertIn("Start Time", header)
        self.assertIn("End Time", header)
        self.assertIn("Venue", header)
        self.assertIn("Status", header)
        self.assertEqual(len(lines), 5)  # 1 header + 4 sample events

    # -------------------------------------------------------------------------
    # Feature 6: Alternative Time Suggestions
    # -------------------------------------------------------------------------
    def test_alternative_time_suggestions(self):
        """Section 8 & 12: List candidate slots with explanations."""
        # Event A is scheduled at 09:00-10:00 in Room 1 with S1
        self.planner.add_event({
            "event_id": "EVT_A",
            "event_name": "Event A",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "09:00",
            "end_time": "10:00",
            "participants": "S1",
        })
        # Event B shares S1 and also uses Room 1
        self.planner.add_event({
            "event_id": "EVT_B",
            "event_name": "Event B",
            "date": "2026-12-05",
            "venue": "Room 1",
            "participants": "S1, S2",
            "preferred_window": "09:00-13:00",
        })

        sugg = self.planner.suggest_slots("EVT_B")
        self.assertEqual(sugg["event_id"], "EVT_B")

        # 09:00-10:00 should be rejected due to participant clash and venue occupancy
        rejected_slots = {r["slot"]: r["reason"] for r in sugg["rejected_slots"]}
        self.assertIn("09:00 - 10:00", rejected_slots)

        # 10:00-11:00 should be rejected because Event A in Room 1 ended at 10:00,
        # needing a 30-min buffer (available only after 10:30)
        self.assertIn("10:00 - 11:00", rejected_slots)

        # 11:00-12:00 is >= 30 mins after Event A, no clashes, inside 09:00-13:00 window -> valid
        valid_slots = {v["slot"]: v["reason"] for v in sugg["valid_slots"]}
        self.assertIn("11:00 - 12:00", valid_slots)
        self.assertIn("buffer", valid_slots["11:00 - 12:00"].lower())

    # -------------------------------------------------------------------------
    # Feature 7: Venue Availability & Configurable Buffer (Section 12 Tests 4, 5, 6)
    # -------------------------------------------------------------------------
    def test_venue_overlap(self):
        """Section 12 Test 4: Room 1 used 10:00-11:00 and 10:30-11:30 -> Venue conflict."""
        self.planner.add_event({
            "event_id": "V1",
            "event_name": "Event 1",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "10:00",
            "end_time": "11:00",
            "participants": "P1",
        })
        self.planner.add_event({
            "event_id": "V2",
            "event_name": "Event 2",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "10:30",
            "end_time": "11:30",
            "participants": "P2",
        })

        val = self.planner.validate_schedule()
        self.assertFalse(val["valid"])
        self.assertTrue(len(val["details"]["venue_overlaps"]) > 0)
        self.assertIn("Hard venue overlap", val["details"]["venue_overlaps"][0])

    def test_buffer_respected_30_min(self):
        """Section 12 Test 5: Previous ends 11:00, next starts 11:30, buffer 30 -> Accepted."""
        self.planner.set_venue_buffer(30)
        self.planner.add_event({
            "event_id": "V1",
            "event_name": "Event 1",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "10:00",
            "end_time": "11:00",
            "participants": "P1",
        })
        self.planner.add_event({
            "event_id": "V2",
            "event_name": "Event 2",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "11:30",
            "end_time": "12:30",
            "participants": "P2",
        })

        val = self.planner.validate_schedule()
        self.assertTrue(val["valid"])
        self.assertEqual(len(val["details"]["buffer_violations"]), 0)

    def test_buffer_too_short_30_min(self):
        """Section 12 Test 6: Previous ends 11:00, next starts 11:20, buffer 30 -> Warning/violation."""
        self.planner.set_venue_buffer(30)
        self.planner.add_event({
            "event_id": "V1",
            "event_name": "Event 1",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "10:00",
            "end_time": "11:00",
            "participants": "P1",
        })
        self.planner.add_event({
            "event_id": "V2",
            "event_name": "Event 2",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "11:20",
            "end_time": "12:20",
            "participants": "P2",
        })

        val = self.planner.validate_schedule()
        self.assertFalse(val["valid"])
        self.assertEqual(len(val["details"]["buffer_violations"]), 1)
        self.assertIn("Insufficient buffer", val["details"]["buffer_violations"][0])

    def test_configurable_buffer_switch(self):
        """Test configuring buffer between 30 and 25 minutes."""
        # 25-minute gap between events
        self.planner.add_event({
            "event_id": "V1",
            "event_name": "Event 1",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "10:00",
            "end_time": "11:00",
            "participants": "P1",
        })
        self.planner.add_event({
            "event_id": "V2",
            "event_name": "Event 2",
            "date": "2026-12-05",
            "venue": "Room 1",
            "start_time": "11:25",
            "end_time": "12:25",
            "participants": "P2",
        })

        # With default 30-min buffer: 25 min gap is a violation
        self.planner.set_venue_buffer(30)
        val30 = self.planner.validate_schedule()
        self.assertEqual(len(val30["details"]["buffer_violations"]), 1)

        # Switch to 25-min buffer: 25 min gap is accepted
        self.planner.set_venue_buffer(25)
        self.assertEqual(self.planner.get_venue_buffer(), 25)
        val25 = self.planner.validate_schedule()
        self.assertEqual(len(val25["details"]["buffer_violations"]), 0)
        self.assertTrue(val25["valid"])

    # -------------------------------------------------------------------------
    # Feature 8: Event Analytics Dashboard
    # -------------------------------------------------------------------------
    def test_event_analytics_metrics(self):
        """Test analytics calculation: counts, dates, venue usage, slot usage."""
        self.planner.load_sample_events()
        self.planner.create_schedule()

        analytics = self.planner.get_analytics()
        self.assertEqual(analytics["total_events"], 4)
        self.assertEqual(analytics["scheduled_events"], 4)
        self.assertEqual(analytics["unassigned_events"], 0)
        self.assertEqual(analytics["participant_clashes_count"], 0)
        self.assertEqual(analytics["venue_overlaps_count"], 0)
        self.assertIn("2026-12-05", analytics["events_per_day"])
        self.assertEqual(analytics["events_per_day"]["2026-12-05"], 4)
        self.assertIn("Lab 2", analytics["venue_usage"])

    # -------------------------------------------------------------------------
    # Feature 9: Manual Timetable Adjustment
    # -------------------------------------------------------------------------
    def test_manual_adjustment_constraint_warning(self):
        """Section 12 Test 8: Move event into conflicting slot -> warn and report conflict."""
        self.planner.add_event({
            "event_id": "E1",
            "event_name": "Event 1",
            "date": "2026-12-05",
            "venue": "Hall A",
            "start_time": "09:00",
            "end_time": "10:00",
            "participants": "S100",
        })
        self.planner.add_event({
            "event_id": "E2",
            "event_name": "Event 2",
            "date": "2026-12-05",
            "venue": "Hall B",
            "start_time": "11:00",
            "end_time": "12:00",
            "participants": "S100",
        })

        # Manually move E2 to 09:30-10:30 (overlaps with E1 on S100)
        success, msg, warnings = self.planner.update_event("E2", {
            "start_time": "09:30",
            "end_time": "10:30",
        })
        self.assertTrue(success)
        self.assertTrue(len(warnings) > 0)
        self.assertIn("Participant clash", warnings[0])

    # -------------------------------------------------------------------------
    # Feature 10: Schedule Validation Report
    # -------------------------------------------------------------------------
    def test_validation_report_completeness(self):
        """Test full validation report separating errors, warnings, and unassigned events."""
        self.planner.add_event({
            "event_id": "UNASS",
            "event_name": "Unassigned Event",
            "date": "2026-12-05",
            "venue": "Room 1",
        })
        val = self.planner.validate_schedule()
        self.assertFalse(val["valid"])
        self.assertIn("UNASS", val["details"]["unassigned_events"][0])


if __name__ == "__main__":
    unittest.main()
