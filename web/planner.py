import csv
import io
import json
from datetime import datetime
from pathlib import Path


class EventPlanner:
    """Stores events and performs conflict detection, scheduling, validation, and analytics."""

    TIME_SLOTS = [
        ("09:00", "10:00"),
        ("10:00", "11:00"),
        ("11:00", "12:00"),
        ("12:00", "13:00"),
        ("13:00", "14:00"),
        ("14:00", "15:00"),
        ("15:00", "16:00"),
        ("16:00", "17:00"),
        ("17:00", "18:00"),
    ]

    DEFAULT_VENUE_BUFFER = 30  # Default venue buffer in minutes

    def __init__(self, data_file):
        self.data_file = Path(data_file)
        self.venue_buffer = self.DEFAULT_VENUE_BUFFER
        self.events = self.load_events()

    def set_venue_buffer(self, minutes):
        """Set the post-session venue buffer (25 or 30 minutes recommended)."""
        try:
            val = int(minutes)
            if val in (25, 30):
                self.venue_buffer = val
                return True, f"Venue buffer set to {val} minutes."
            if val > 0:
                self.venue_buffer = val
                return True, f"Venue buffer set to {val} minutes."
            return False, "Buffer must be a positive number of minutes (25 or 30 recommended)."
        except (ValueError, TypeError):
            return False, "Invalid buffer value."

    def get_venue_buffer(self):
        """Return the current venue buffer in minutes."""
        return self.venue_buffer

    def load_events(self):
        """Load saved events. Start empty if the file is missing or damaged."""
        if not self.data_file.exists():
            return {}

        try:
            with self.data_file.open("r", encoding="utf-8") as file:
                events = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}

        if isinstance(events, dict):
            return events
        return {}

    def save_events(self):
        """Save all events to the JSON file."""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        with self.data_file.open("w", encoding="utf-8") as file:
            json.dump(self.events, file, indent=2)

    def list_events(self):
        """Return events ordered by date and time."""
        return sorted(
            self.events.values(),
            key=lambda event: (
                event.get("date", ""),
                event.get("start_time") or "99:99",
                event.get("event_id", ""),
            ),
        )

    def get_event(self, event_id):
        """Return a single event by ID or None."""
        return self.events.get(str(event_id).upper())

    def _next_event_id(self):
        """Generate the next available EVT### ID."""
        existing = set(self.events.keys())
        n = 1
        while True:
            candidate = f"EVT{n:03d}"
            if candidate not in existing:
                return candidate
            n += 1

    def add_event(self, details):
        """Check form details and add one event."""
        # Auto-generate ID if not supplied
        event_id = self.get_text(details, "event_id").upper()
        if not event_id:
            event_id = self._next_event_id()

        event_name = self.get_text(details, "event_name")
        date = self.get_text(details, "date")
        venue = self.get_text(details, "venue")
        start_time = self.get_text(details, "start_time")
        end_time = self.get_text(details, "end_time")
        preferred_window = self.get_text(details, "preferred_window")

        if not event_name or not date or not venue:
            return False, "Event name, date, and venue are required."

        if event_id in self.events:
            event_id = self._next_event_id()  # skip collision silently

        if not self.valid_date(date):
            return False, "Use YYYY-MM-DD for the date."

        if bool(start_time) != bool(end_time):
            return False, "Enter both start time and end time, or leave both blank for auto-assignment."

        if start_time:
            if not self.valid_time(start_time) or not self.valid_time(end_time):
                return False, "Use HH:MM (24-hour) for start and end times."
            if self.time_as_minutes(start_time) >= self.time_as_minutes(end_time):
                return False, "End time must be later than start time."

        if preferred_window:
            valid_pw, pw_err = self.validate_time_window(preferred_window)
            if not valid_pw:
                return False, pw_err

        participants = self.make_participant_list(details.get("participants"))

        new_event = {
            "event_id": event_id,
            "event_name": event_name,
            "date": date,
            "venue": venue,
            "participants": participants,
            "preferred_window": preferred_window or None,
            "description": self.get_text(details, "description"),
            "start_time": start_time or None,
            "end_time": end_time or None,
            "status": "Scheduled" if start_time else "Unassigned",
        }

        self.events[event_id] = new_event
        self.save_events()

        # Check for immediate warnings if scheduled manually
        warnings = []
        if start_time:
            warnings = self.check_event_conflicts_inline(new_event)

        message = f"Event '{event_name}' added with ID {event_id}."
        if warnings:
            message += f" {'; '.join(warnings)}"

        # Return 4-tuple: (success, message, event_id, warnings)
        # Callers unpacking only 2 values should use: success, msg = result[:2]
        return True, message, event_id, warnings

    def update_event(self, event_id, details):
        """Update an existing event with immediate constraint checking."""
        event_id = str(event_id).upper()
        if event_id not in self.events:
            return False, "Event was not found.", []

        event = self.events[event_id]

        event_name = self.get_text(details, "event_name") or event["event_name"]
        date = self.get_text(details, "date") or event["date"]
        venue = self.get_text(details, "venue") or event["venue"]

        # Check if times are being explicitly updated or cleared
        if "start_time" in details or "end_time" in details:
            start_time = self.get_text(details, "start_time")
            end_time = self.get_text(details, "end_time")
        else:
            start_time = event.get("start_time") or ""
            end_time = event.get("end_time") or ""

        preferred_window = (
            self.get_text(details, "preferred_window")
            if "preferred_window" in details
            else (event.get("preferred_window") or "")
        )

        if not self.valid_date(date):
            return False, "Use YYYY-MM-DD for the date.", []

        if bool(start_time) != bool(end_time):
            return False, "Enter both start time and end time, or leave both blank to unassign.", []

        if start_time:
            if not self.valid_time(start_time) or not self.valid_time(end_time):
                return False, "Use HH:MM (24-hour) for start and end times.", []
            if self.time_as_minutes(start_time) >= self.time_as_minutes(end_time):
                return False, "End time must be later than start time.", []

        if preferred_window:
            valid_pw, pw_err = self.validate_time_window(preferred_window)
            if not valid_pw:
                return False, pw_err, []

        participants = (
            self.make_participant_list(details["participants"])
            if "participants" in details
            else event["participants"]
        )

        description = (
            self.get_text(details, "description")
            if "description" in details
            else event.get("description", "")
        )

        updated_event = {
            "event_id": event_id,
            "event_name": event_name,
            "date": date,
            "venue": venue,
            "participants": participants,
            "preferred_window": preferred_window or None,
            "description": description,
            "start_time": start_time or None,
            "end_time": end_time or None,
            "status": "Scheduled" if start_time else "Unassigned",
        }

        # Check immediate constraints
        warnings = self.check_event_conflicts_inline(updated_event, exclude_id=event_id)

        self.events[event_id] = updated_event
        self.save_events()

        msg = "Event updated successfully."
        if warnings:
            msg += f" Notice: {len(warnings)} conflict warning(s) detected."

        return True, msg, warnings

    def delete_event(self, event_id):
        """Remove an event."""
        event_id = str(event_id).upper()
        if event_id not in self.events:
            return False, "Event was not found."

        del self.events[event_id]
        self.save_events()
        return True, "Event deleted."

    def load_sample_events(self):
        """Load standard sample events according to the project specification.

        Returns the number of events loaded for display in the UI.
        """
        sample_events = [
            (
                "EVT001",
                "Python Workshop",
                "S101, S102, S103",
                "Lab 2",
                "09:00-13:00",
                "Hands-on Python programming",
            ),
            (
                "EVT002",
                "Web Development Seminar",
                "S102, S104, S105",
                "Hall 1",
                "09:00-14:00",
                "Modern frontend & backend architectures",
            ),
            (
                "EVT003",
                "AI and ML Talk",
                "S103, S106, S107",
                "Lab 2",
                "10:00-15:00",
                "Keynote on machine intelligence",
            ),
            (
                "EVT004",
                "Hackathon",
                "S108, S109, S110",
                "Lab 3",
                "09:00-18:00",
                "24-hour coding challenge",
            ),
        ]

        self.events = {}
        for event_id, name, participants, venue, window, desc in sample_events:
            self.events[event_id] = {
                "event_id": event_id,
                "event_name": name,
                "date": "2026-12-05",
                "venue": venue,
                "participants": self.make_participant_list(participants),
                "preferred_window": window,
                "description": desc,
                "start_time": None,
                "end_time": None,
                "status": "Unassigned",
            }

        self.save_events()
        return len(self.events)

    def get_text(self, details, key):
        """Safely extract string text from a dictionary."""
        value = details.get(key, "")
        if value is None:
            return ""
        return str(value).strip()

    def make_participant_list(self, value):
        """Convert participant text or a list into a sorted list of unique IDs."""
        if isinstance(value, list):
            value = ",".join(str(item) for item in value)

        participant_ids = set()
        for item in str(value or "").split(","):
            item = item.strip().upper()
            if item:
                participant_ids.add(item)

        return sorted(participant_ids)

    def validate_time_window(self, window_str):
        """Validate preferred time window format, e.g., '09:00-13:00'."""
        if not window_str:
            return True, ""
        parts = window_str.replace("–", "-").split("-")
        if len(parts) != 2:
            return False, "Preferred window format must be 'HH:MM-HH:MM' (e.g. 09:00-13:00)."
        start, end = parts[0].strip(), parts[1].strip()
        if not self.valid_time(start) or not self.valid_time(end):
            return False, "Use valid HH:MM times for preferred window."
        if self.time_as_minutes(start) >= self.time_as_minutes(end):
            return False, "Preferred window end time must be later than start time."
        return True, ""

    def get_event_pairs(self):
        """Return each pair of distinct events only once."""
        events = list(self.events.values())
        pairs = []

        for first_index in range(len(events)):
            first = events[first_index]
            for second_index in range(first_index + 1, len(events)):
                second = events[second_index]
                pairs.append((first, second))

        return pairs

    def get_shared_participants(self, first, second):
        """Find participant IDs that appear in both events using set intersection."""
        first_participants = set(first.get("participants", []))
        second_participants = set(second.get("participants", []))
        return first_participants.intersection(second_participants)

    def build_conflict_graph(self):
        """Build conflict graph where vertices are events and edges connect events sharing participants on the same date."""
        graph = {event_id: set() for event_id in self.events}

        for first, second in self.get_event_pairs():
            if first.get("date") == second.get("date"):
                shared = self.get_shared_participants(first, second)
                if shared:
                    first_id = first["event_id"]
                    second_id = second["event_id"]
                    graph[first_id].add(second_id)
                    graph[second_id].add(first_id)

        return graph

    def get_priority_ranking(self):
        """Rank events by scheduling difficulty using conflict degree with transparent tie-breakers.

        Priority order:
        1. Conflict degree (number of edges in conflict graph, descending)
        2. Participant count (descending)
        3. Event ID (ascending)
        """
        graph = self.build_conflict_graph()
        ranking = []

        for event_id, event in self.events.items():
            conflicting_ids = sorted(graph.get(event_id, set()))
            degree = len(conflicting_ids)
            part_count = len(event.get("participants", []))

            ranking.append({
                "event_id": event_id,
                "event_name": event.get("event_name", ""),
                "date": event.get("date", ""),
                "venue": event.get("venue", ""),
                "conflict_degree": degree,
                "participant_count": part_count,
                "conflicts_with_ids": conflicting_ids,
                "conflicts_with_names": [
                    self.events[other_id]["event_name"]
                    for other_id in conflicting_ids
                    if other_id in self.events
                ],
                "status": event.get("status", "Unassigned"),
            })

        ranking.sort(
            key=lambda item: (
                -item["conflict_degree"],
                -item["participant_count"],
                item["event_id"],
            )
        )

        for index, item in enumerate(ranking, start=1):
            item["rank"] = index

        return ranking

    def check_event_conflicts_inline(self, target_event, exclude_id=None):
        """Check participant and venue conflicts for a single event against all other scheduled events."""
        warnings = []
        if not target_event.get("start_time") or not target_event.get("end_time"):
            return warnings

        t_date = target_event.get("date")
        t_venue = target_event.get("venue")
        t_slot = (target_event["start_time"], target_event["end_time"])
        t_participants = set(target_event.get("participants", []))

        for other_id, other in self.events.items():
            if exclude_id and other_id == exclude_id:
                continue
            if other.get("event_id") == target_event.get("event_id"):
                continue
            if not other.get("start_time") or not other.get("end_time"):
                continue
            if other.get("date") != t_date:
                continue

            o_slot = (other["start_time"], other["end_time"])

            # Participant clash check
            shared = t_participants.intersection(set(other.get("participants", [])))
            if shared and self.slots_overlap(t_slot, o_slot):
                warnings.append(
                    f"Participant clash with {other['event_name']} ({other_id}) "
                    f"at {other['start_time']}-{other['end_time']} for student(s): {', '.join(sorted(shared))}."
                )

            # Venue check
            if other.get("venue") == t_venue:
                if self.slots_overlap(t_slot, o_slot):
                    warnings.append(
                        f"Hard venue overlap: {t_venue} is already in use by {other['event_name']} "
                        f"({other_id}) at {other['start_time']}-{other['end_time']}."
                    )
                elif self.slots_are_too_close(t_slot, o_slot):
                    warnings.append(
                        f"Venue buffer violation: {t_venue} requires a {self.venue_buffer}-minute buffer "
                        f"before/after {other['event_name']} ({other_id}, {other['start_time']}-{other['end_time']})."
                    )

        return warnings

    def find_conflicts(self):
        """Return comprehensive conflict report distinguishing simultaneous participant clashes and shared-participant graph connections."""
        clashes = []
        potential_conflicts = []

        for first, second in self.get_event_pairs():
            if first.get("date") != second.get("date"):
                continue

            shared = self.get_shared_participants(first, second)
            if not shared:
                continue

            both_scheduled = bool(first.get("start_time") and second.get("start_time"))
            overlap = both_scheduled and self.events_overlap(first, second)

            item = {
                "first_id": first["event_id"],
                "first_event": first["event_name"],
                "first_time": f"{first['start_time']}-{first['end_time']}" if first.get("start_time") else "Unassigned",
                "second_id": second["event_id"],
                "second_event": second["event_name"],
                "second_time": f"{second['start_time']}-{second['end_time']}" if second.get("start_time") else "Unassigned",
                "date": first["date"],
                "shared_participants": sorted(shared),
                "is_simultaneous_clash": overlap,
            }

            if overlap:
                clashes.append(item)
            potential_conflicts.append(item)

        return {
            "simultaneous_clashes": clashes,
            "potential_conflicts": potential_conflicts,
        }

    def slot_fits_window(self, slot, preferred_window):
        """Check if candidate slot falls completely inside the preferred window."""
        if not preferred_window:
            return True
        try:
            parts = preferred_window.replace("–", "-").split("-")
            win_start = self.time_as_minutes(parts[0].strip())
            win_end = self.time_as_minutes(parts[1].strip())
            slot_start, slot_end = self.slot_as_minutes(slot)
            return slot_start >= win_start and slot_end <= win_end
        except (ValueError, IndexError):
            return True

    def slot_is_available(self, event_id, candidate_slot, graph, scheduled):
        """Check whether candidate slot is valid against participant and venue rules."""
        event = self.events[event_id]

        # 1. Preferred time window check
        pref_window = event.get("preferred_window")
        if pref_window and not self.slot_fits_window(candidate_slot, pref_window):
            return False, f"Outside preferred window ({pref_window})"

        # 2. Conflict graph (participant sharing) check
        for other_id in graph.get(event_id, set()):
            other_slot = scheduled.get(other_id)
            if other_slot and self.slots_overlap(candidate_slot, other_slot):
                other_name = self.events[other_id]["event_name"]
                shared = self.get_shared_participants(event, self.events[other_id])
                return False, f"Participant clash with {other_name} ({other_id}) over {', '.join(sorted(shared))}"

        # 3. Venue occupancy and buffer check
        for other_id, other_slot in scheduled.items():
            if other_id == event_id:
                continue
            other_event = self.events[other_id]
            if event.get("date") == other_event.get("date") and event.get("venue") == other_event.get("venue"):
                if self.slots_overlap(candidate_slot, other_slot):
                    return False, f"Venue {event['venue']} occupied by {other_event['event_name']} ({other_id})"
                if self.slots_are_too_close(candidate_slot, other_slot):
                    return False, f"Venue {event['venue']} requires {self.venue_buffer}-minute buffer after/before {other_event['event_name']} ({other_id})"

        return True, "Available"

    def suggest_slots(self, event_id):
        """List candidate slots that satisfy participant, venue, duration, and buffer rules with reasons."""
        event_id = str(event_id).upper()
        if event_id not in self.events:
            return {"error": "Event not found."}

        event = self.events[event_id]
        graph = self.build_conflict_graph()

        # Build map of currently scheduled events (excluding target event)
        scheduled = {}
        for other_id, other in self.events.items():
            if other_id != event_id and other.get("start_time") and other.get("end_time"):
                scheduled[other_id] = (other["start_time"], other["end_time"])

        valid_suggestions = []
        rejected_slots = []

        for slot in self.TIME_SLOTS:
            is_valid, reason = self.slot_is_available(event_id, slot, graph, scheduled)
            slot_str = f"{slot[0]} - {slot[1]}"
            if is_valid:
                valid_suggestions.append({
                    "slot": slot_str,
                    "start_time": slot[0],
                    "end_time": slot[1],
                    "reason": f"No shared-participant clash; {event['venue']} available with {self.venue_buffer}-minute buffer.",
                })
            else:
                rejected_slots.append({
                    "slot": slot_str,
                    "start_time": slot[0],
                    "end_time": slot[1],
                    "reason": reason,
                })

        summary = (
            f"Found {len(valid_suggestions)} valid slot(s) for {event['event_name']} ({event_id})."
            if valid_suggestions
            else f"No valid slots found for {event['event_name']} ({event_id}). All candidate slots have conflicts."
        )

        return {
            "event_id": event_id,
            "event_name": event["event_name"],
            "venue": event["venue"],
            "preferred_window": event.get("preferred_window") or "None specified",
            "venue_buffer": self.venue_buffer,
            "summary": summary,
            "valid_slots": valid_suggestions,
            "rejected_slots": rejected_slots,
        }

    def create_schedule(self):
        """Assign timetable slots using greedy graph coloring ordered by conflict priority.

        Manually scheduled events (those already having start/end times) are
        preserved.  All other events are cleared and re-assigned from scratch
        so that repeated clicks of "Create schedule" produce a fresh greedy
        result rather than silently keeping stale auto-assignments.
        """
        graph = self.build_conflict_graph()
        scheduled = {}
        assignments = []
        unassigned_explanations = {}

        # Preserve only manually fixed events (ones that had times before this call)
        for event in self.events.values():
            if event.get("start_time") and event.get("end_time"):
                scheduled[event["event_id"]] = (
                    event["start_time"],
                    event["end_time"],
                )
                event["status"] = "Scheduled"
            else:
                event["start_time"] = None
                event["end_time"] = None
                event["status"] = "Unassigned"

        # Sort unassigned events by priority ranking (degree desc, participant count desc, event_id asc)
        ranked = self.get_priority_ranking()
        ranked_ids = [item["event_id"] for item in ranked]

        for event_id in ranked_ids:
            if event_id in scheduled:
                continue

            event = self.events[event_id]
            assigned_slot = None
            slot_block_reasons = []

            for slot in self.TIME_SLOTS:
                available, reason = self.slot_is_available(event_id, slot, graph, scheduled)
                if available:
                    assigned_slot = slot
                    break
                else:
                    slot_block_reasons.append(f"{slot[0]}-{slot[1]}: {reason}")

            if assigned_slot:
                scheduled[event_id] = assigned_slot
                event["start_time"] = assigned_slot[0]
                event["end_time"] = assigned_slot[1]
                event["status"] = "Scheduled"
                assignments.append({
                    "event_id": event_id,
                    "event_name": event["event_name"],
                    "slot": f"{assigned_slot[0]} - {assigned_slot[1]}",
                    "venue": event["venue"],
                })
            else:
                unassigned_explanations[event_id] = {
                    "event_name": event["event_name"],
                    "reason": "All candidate slots violated participant, venue, or buffer constraints.",
                    "details": slot_block_reasons[:3],  # top reasons
                }

        self.save_events()

        return {
            "scheduled": len(scheduled),
            "unassigned": len(self.events) - len(scheduled),
            "assignments": assignments,
            "unassigned_explanations": unassigned_explanations,
        }

    def validate_schedule(self):
        """Validate timetable: participant clashes, venue overlaps, buffer violations, and unassigned events."""
        errors = []
        warnings = []
        details = {
            "participant_clashes": [],
            "venue_overlaps": [],
            "buffer_violations": [],
            "unassigned_events": [],
            "missing_data": [],
        }

        # Check missing fields and unassigned status
        for event_id, event in self.events.items():
            if not event.get("date"):
                details["missing_data"].append(f"{event_id} ({event.get('event_name', '')}) is missing a date.")
                errors.append(f"{event_id}: Missing date.")
            if not event.get("venue"):
                details["missing_data"].append(f"{event_id} ({event.get('event_name', '')}) is missing a venue.")
                errors.append(f"{event_id}: Missing venue.")
            if not event.get("start_time") or not event.get("end_time"):
                details["unassigned_events"].append(f"{event_id} ({event.get('event_name', '')}) has not been scheduled.")
                warnings.append(f"{event_id} ({event.get('event_name', '')}) is unassigned.")

        # Check pairs
        for first, second in self.get_event_pairs():
            if not first.get("start_time") or not second.get("start_time"):
                continue
            if first.get("date") != second.get("date"):
                continue

            first_slot = (first["start_time"], first["end_time"])
            second_slot = (second["start_time"], second["end_time"])
            first_start, first_end = self.slot_as_minutes(first_slot)
            second_start, second_end = self.slot_as_minutes(second_slot)

            # 1. Participant clash
            shared = self.get_shared_participants(first, second)
            overlap = self.slots_overlap(first_slot, second_slot)
            if shared and overlap:
                names = ", ".join(sorted(shared))
                msg = (
                    f"Participant clash: {first['event_name']} ({first['event_id']}) and "
                    f"{second['event_name']} ({second['event_id']}) overlap at "
                    f"{first['start_time']}-{first['end_time']} vs {second['start_time']}-{second['end_time']} "
                    f"for participant(s): {names}."
                )
                errors.append(msg)
                details["participant_clashes"].append(msg)

            # 2. Venue check
            if first.get("venue") == second.get("venue"):
                if overlap:
                    msg = (
                        f"Hard venue overlap: {first['event_name']} ({first['event_id']}) and "
                        f"{second['event_name']} ({second['event_id']}) both occupy {first['venue']} "
                        f"simultaneously ({first['start_time']}-{first['end_time']} vs {second['start_time']}-{second['end_time']})."
                    )
                    errors.append(msg)
                    details["venue_overlaps"].append(msg)
                elif self.slots_are_too_close(first_slot, second_slot):
                    # Buffer violation
                    gap = min(
                        abs(first_start - second_end),
                        abs(second_start - first_end),
                    )
                    msg = (
                        f"Insufficient buffer: {first['event_name']} ({first['event_id']}) and "
                        f"{second['event_name']} ({second['event_id']}) have only a {gap}-minute gap in {first['venue']}. "
                        f"Configured buffer requires {self.venue_buffer} minutes."
                    )
                    warnings.append(msg)
                    details["buffer_violations"].append(msg)

        is_valid = len(errors) == 0 and len(details["buffer_violations"]) == 0 and len(details["unassigned_events"]) == 0

        return {
            "valid": is_valid,
            "has_critical_errors": len(errors) > 0,
            "errors": errors,
            "warnings": warnings,
            "details": details,
            "venue_buffer": self.venue_buffer,
        }

    def get_analytics(self):
        """Calculate event analytics dashboard metrics."""
        total_events = len(self.events)
        scheduled_count = sum(1 for e in self.events.values() if e.get("status") == "Scheduled")
        unassigned_count = total_events - scheduled_count

        # Events per day
        events_per_day = {}
        for event in self.events.values():
            d = event.get("date") or "Unknown"
            events_per_day[d] = events_per_day.get(d, 0) + 1

        # Venue usage & minutes
        venue_usage = {}
        for event in self.events.values():
            venue = event.get("venue") or "Unassigned Venue"
            if venue not in venue_usage:
                venue_usage[venue] = {"events_count": 0, "total_minutes": 0, "events": []}
            venue_usage[venue]["events_count"] += 1
            if event.get("start_time") and event.get("end_time"):
                try:
                    duration = self.time_as_minutes(event["end_time"]) - self.time_as_minutes(event["start_time"])
                    venue_usage[venue]["total_minutes"] += max(0, duration)
                except Exception:
                    pass
            venue_usage[venue]["events"].append(event.get("event_name"))

        # Slot usage
        slot_usage = {f"{s[0]}-{s[1]}": 0 for s in self.TIME_SLOTS}
        for event in self.events.values():
            if event.get("start_time") and event.get("end_time"):
                slot_key = f"{event['start_time']}-{event['end_time']}"
                if slot_key in slot_usage:
                    slot_usage[slot_key] += 1
                else:
                    slot_usage[slot_key] = slot_usage.get(slot_key, 0) + 1

        # Conflicts counts
        conflict_data = self.find_conflicts()
        val = self.validate_schedule()

        return {
            "total_events": total_events,
            "scheduled_events": scheduled_count,
            "unassigned_events": unassigned_count,
            "events_per_day": events_per_day,
            "participant_clashes_count": len(conflict_data["simultaneous_clashes"]),
            "potential_conflicts_count": len(conflict_data["potential_conflicts"]),
            "venue_overlaps_count": len(val["details"]["venue_overlaps"]),
            "buffer_violations_count": len(val["details"]["buffer_violations"]),
            "venue_usage": venue_usage,
            "slot_usage": slot_usage,
            "venue_buffer": self.venue_buffer,
        }

    def export_csv_data(self):
        """Generate timetable CSV rows formatted according to the project specification."""
        fields = [
            "Event ID",
            "Event Name",
            "Date",
            "Start Time",
            "End Time",
            "Venue",
            "Participants",
            "Status",
        ]
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n",
                                extrasaction="ignore")
        writer.writeheader()

        for event in self.list_events():
            # Format date as DD-MM-YYYY for readability in spreadsheets
            raw_date = event.get("date", "")
            try:
                formatted_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            except (ValueError, TypeError):
                formatted_date = raw_date

            writer.writerow({
                "Event ID": event.get("event_id", ""),
                "Event Name": event.get("event_name", ""),
                "Date": formatted_date,
                "Start Time": event.get("start_time") or "Unassigned",
                "End Time": event.get("end_time") or "",
                "Venue": event.get("venue", ""),
                "Participants": ", ".join(event.get("participants", [])),
                "Status": event.get("status", "Unassigned"),
            })

        return output.getvalue()

    def slots_are_too_close(self, first_slot, second_slot):
        """Return True when two non-overlapping event time ranges in the same venue
        are closer than the venue buffer.  Overlapping slots are NOT flagged here;
        callers must check slots_overlap() first for a hard overlap."""
        first_start, first_end = self.slot_as_minutes(first_slot)
        second_start, second_end = self.slot_as_minutes(second_slot)

        # If the slots actually overlap, this is a hard venue conflict, not a buffer issue.
        if first_start < second_end and second_start < first_end:
            return False

        # Calculate the gap between the two non-overlapping intervals.
        gap = max(second_start - first_end, first_start - second_end)
        return gap < self.venue_buffer

    def slots_overlap(self, first_slot, second_slot):
        """Return True when two event time ranges overlap."""
        first_start, first_end = self.slot_as_minutes(first_slot)
        second_start, second_end = self.slot_as_minutes(second_slot)
        return first_start < second_end and second_start < first_end

    def events_overlap(self, first, second):
        """Return True when both events have times and the times overlap."""
        first_slot = (first["start_time"], first["end_time"])
        second_slot = (second["start_time"], second["end_time"])
        return self.slots_overlap(first_slot, second_slot)

    def valid_date(self, date):
        """Accept a real calendar date in YYYY-MM-DD format."""
        try:
            datetime.strptime(date, "%Y-%m-%d")
            return True
        except (TypeError, ValueError):
            return False

    def valid_time(self, time):
        """Accept a time in HH:MM format."""
        try:
            hour, minute = time.split(":")
            hour = int(hour)
            minute = int(minute)
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (AttributeError, TypeError, ValueError):
            return False

    def slot_as_minutes(self, slot):
        """Convert a time pair into minutes after midnight."""
        start = self.time_as_minutes(slot[0])
        end = self.time_as_minutes(slot[1])
        return start, end

    def time_as_minutes(self, time):
        """Convert a string such as 09:30 into minutes."""
        parts = time.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours * 60 + minutes
