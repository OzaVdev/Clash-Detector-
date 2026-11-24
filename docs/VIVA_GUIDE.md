# Viva Guide: College Event Planner Web App

## One-line introduction

This project is a web application that schedules college events while avoiding shared-participant and venue conflicts. It uses set intersection and greedy graph coloring.

## How do I run it?

```bash
python main.py
```

Then open `http://localhost:8000` in a browser.

## What does each folder do?

| Location | Responsibility |
| --- | --- |
| `main.py` | Starts the local web server. |
| `web/server.py` | Receives requests from the browser and returns data. |
| `web/planner.py` | Contains event storage, conflict checking, scheduling, and validation. |
| `web/static/index.html` | Page structure. |
| `web/static/style.css` | Page design. |
| `web/static/app.js` | Button actions and page updates. |
| `data/events.json` | Saved events. |

## MFCS concept 1: set intersection

Each event has participant IDs. To find students registered for both events, the program uses set intersection:

```python
set(first["participants"]).intersection(second["participants"])
```

Example:

```text
Python Workshop = {S101, S102, S103}
Web Seminar     = {S102, S104, S105}
Intersection    = {S102}
```

Because `S102` is in both events, the events must not occur at the same time.

## MFCS concept 2: graph coloring

- Each event is a **vertex**.
- Two events are connected by an **edge** if they have common participants on the same date.
- Each time slot is a **color**.
- Connected vertices must have different colors.

The conflict graph is represented in the code as an adjacency list, for example:

```text
EVT001: {EVT002}
EVT002: {EVT001}
```

## Why use greedy graph coloring?

1. Count the conflicts of every event.
2. Schedule events with more conflicts first.
3. Try the available slots from 09:00 to 18:00.
4. Assign the first slot that has no participant or venue conflict.

It is called greedy because it selects the first valid option and does not go back to change earlier decisions. It is easy to understand and suitable for a small college project, although it does not always find the theoretical best timetable.

## Venue rule

The same venue cannot host two events at overlapping times. This project also requires a 30-minute gap after one event before the next event in the same venue.

## Demonstration steps

1. Run the application and open the web page.
2. Click **Load sample events**.
3. Click **Show conflicts**. Explain the shared participant IDs.
4. Click **Create schedule**. Explain graph coloring.
5. Click **Check schedule**. Show that the schedule is valid.
6. Click **Download CSV**. Open the exported timetable in Excel if needed.

## Useful questions and answers

**What is a conflict?**

Two same-day events conflict when they share at least one participant, because that participant cannot attend both events at the same time.

**Why are events with more conflicts scheduled first?**

They have fewer valid choices, so scheduling them first reduces the chance that they remain unassigned.

**What is the time complexity?**

Building the conflict graph compares pairs of events, so it is approximately O(n²). For a small college event list, this is fast enough.

**What is a limitation?**

Time slots are fixed one-hour slots from 09:00 to 18:00. The algorithm is greedy, so it prioritises simplicity and speed over finding an always-optimal timetable.
