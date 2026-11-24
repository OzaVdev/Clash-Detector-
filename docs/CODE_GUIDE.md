# Beginner Code Guide

This guide explains the project architecture, data structures, and algorithms in beginner-friendly language for study and viva examination.

---

## 1. Application Entry Point: `main.py`

```python
from web.server import start_server

if __name__ == "__main__":
    start_server()
```

- Starts the local HTTP server on port 8000.
- Serves the frontend web UI and handles RESTful API requests.

---

## 2. Web Server: `web/server.py`

Built strictly using Python's standard `http.server.ThreadingHTTPServer` and `BaseHTTPRequestHandler`.

### Key Handler Methods:
- `do_GET()`: Serves HTML, CSS, JavaScript, and read-only endpoints:
  - `/api/events`: Event list
  - `/api/events/<id>`: Single event
  - `/api/events/<id>/suggestions`: Candidate slots
  - `/api/conflicts`: Shared participant report
  - `/api/priority`: Scheduling difficulty ranking
  - `/api/validation`: Schedule integrity checks
  - `/api/analytics`: Metrics dashboard
  - `/api/buffer`: Venue buffer settings
  - `/api/export`: CSV timetable download
- `do_POST()`: Creates events, loads sample benchmarks, runs scheduler, or updates buffer settings.
- `do_PUT()`: Handles `/api/events/<id>` to support manual event adjustments and immediate constraint validation.
- `do_DELETE()`: Removes an event by ID.

---

## 3. Core Engine: `web/planner.py`

The `EventPlanner` class manages all data and implements MFCS algorithms.

### 3.1 Event Data Structure
Each event is stored in `self.events` keyed by its uppercase ID:
```python
{
    "event_id": "EVT001",
    "event_name": "Python Workshop",
    "date": "2026-12-05",
    "venue": "Lab 2",
    "preferred_window": "09:00-13:00",
    "participants": ["S101", "S102", "S103"],
    "description": "Hands-on workshop",
    "start_time": "09:00",
    "end_time": "10:00",
    "status": "Scheduled"
}
```

### 3.2 Conflict Graph Construction (`build_conflict_graph`)
- **Vertices:** Events in `self.events`.
- **Edges:** Connect two events on the same date whose participant sets have a non-empty intersection.
```python
shared = set(first["participants"]).intersection(set(second["participants"]))
if shared and first["date"] == second["date"]:
    graph[first["event_id"]].add(second["event_id"])
    graph[second["event_id"]].add(first["event_id"])
```

### 3.3 Smart Priority Ranking (`get_priority_ranking`)
Events with higher conflict degree have more constraints and fewer safe coloring choices:
1. Primary sort: **Conflict degree** (descending)
2. Secondary sort: **Participant count** (descending)
3. Tertiary sort: **Event ID** (ascending)

### 3.4 Greedy Graph Coloring (`create_schedule`)
1. Sort unassigned events by priority ranking.
2. For each candidate slot in `TIME_SLOTS`:
   - Verify slot is inside `preferred_window` (if specified).
   - Verify no adjacent graph neighbour uses an overlapping slot.
   - Verify venue is not occupied.
   - Verify post-session venue buffer (25 or 30 minutes) is respected.
3. Assign the first valid slot. If no slot satisfies all constraints, mark event as `Unassigned` and record the blocking constraint reason.

### 3.5 Alternative Time Suggestions (`suggest_slots`)
Evaluates all available discrete time slots for a given event, checking participant clashes and venue buffer gaps. Returns valid candidate slots with clear reasons, or explanations of blocking constraints.

### 3.6 Configurable Venue Buffer (`set_venue_buffer`)
Enforces a configurable 25- or 30-minute buffer (default: 30 minutes) between sessions in the same room. Distinguishes hard venue overlaps from buffer violations.

### 3.7 Validation Report (`validate_schedule`)
Performs a full audit and categorizes findings:
- **Errors:** Simultaneous participant clashes, hard venue overlaps, missing dates/venues.
- **Warnings:** Insufficient room buffer gaps, unassigned events.

### 3.8 Analytics Summary (`get_analytics`)
Computes metrics including total events, scheduled vs unassigned ratio, participant clashes, venue overlaps, room utilization hours, and slot usage distributions.

---

## 4. Frontend: HTML, CSS, JavaScript

- **`web/static/index.html`:** Semantic HTML5 layout featuring action toolbar, add event form, timetable table, edit modal, and analytics panels.
- **`web/static/style.css`:** Clean, responsive design with distinct color-coded badges for errors (red), warnings (amber), and successes (green).
- **`web/static/app.js`:** Vanilla JavaScript interacting with the RESTful API via `fetch()`, dynamic DOM rendering, and instant feedback.

---

## 5. Automated Tests: `tests/`

- **`tests/test_planner.py`:** 19 unit tests verifying each feature and scenario outlined in Section 12 of the project specification.
- **`tests/test_server.py`:** Integration tests verifying all HTTP server endpoints, headers, and CSV exports.
