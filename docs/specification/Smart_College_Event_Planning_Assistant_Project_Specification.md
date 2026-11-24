**SMART COLLEGE EVENT  
PLANNING ASSISTANT**

Complete Project Specification

_A beginner-friendly Python application for event conflict detection,  
scheduling support, venue checks, and shareable timetables._

| **Project profile**     | **Specification**                                        |
| ----------------------- | -------------------------------------------------------- |
| Domain                  | College event planning and timetable management          |
| Language                | Python 3                                                 |
| Primary MFCS concept    | Graph Theory — Graph Coloring                            |
| Supporting MFCS concept | Set Theory — Sets and Set Intersection                   |
| Implementation style    | Explainable, rule-based algorithms; no ML model required |
| Audience                | Student, faculty, developer, or another LLM              |

Version 1.0 | November 2026

# 1. Project Overview

Smart College Event Planning Assistant is a Python application that helps college organisers plan multiple events while avoiding participant clashes and venue conflicts. It stores event details, detects shared participants, checks venue availability, helps assign time slots, suggests alternatives, validates the schedule, displays basic analytics, and exports a timetable for students.

The central mathematical model is graph coloring. Events are vertices; an edge connects two events that cannot occur simultaneously; and each color represents a time slot. Set intersection identifies students registered for more than one event.

# 2. Problem Statement

Colleges conduct workshops, competitions, seminars, club activities, and technical sessions. When several events are planned on the same day, students may register for multiple events and organisers may allocate the same venue to overlapping sessions. Manual coordination can cause clashes, last-minute changes, and confusing communication. This system provides structured event records, conflict detection, venue checks, scheduling support, validation, and a shareable timetable.

# 3. Objectives

- Maintain event details in one place.
- Detect shared participants and scheduled clashes.
- Rank events using a transparent conflict-based priority rule.
- Generate a conflict-aware timetable using greedy graph coloring, if the optional feature is completed.
- Check venue occupancy and enforce a configurable 25–30 minute post-session buffer.
- Suggest alternative slots when a proposed slot is unsuitable.
- Allow manual timetable changes and revalidate them.
- Provide event analytics, a validation report, and a shareable export.

# 4. Finalised Feature Scope

All ten selected features are part of the agreed scope. Automatic timetable generation is included as a planned/optional feature: the system must remain useful through manual scheduling and validation if automatic generation is not completed.

| **Feature**                        | **Priority**       | **Description**                                                                                                                                                                           |
| ---------------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1\. Event details management       | Core               | Add, view, edit, and delete events. Store event name, date, start/end time or duration, participant IDs, preferred time window, venue, and optional description.                          |
| 2\. Automatic conflict detection   | Core               | Compare participant sets. Report shared student IDs and identify a participant clash when the events' scheduled intervals overlap.                                                        |
| 3\. Smart event priority           | Core               | Rank scheduling difficulty using conflict degree: the number of other events connected to an event in the conflict graph. Highest degree is processed first.                              |
| 4\. Automatic timetable generation | Optional / planned | Use greedy graph coloring to assign candidate time slots so connected events receive different slots. Manual scheduling and validation remain available if this is not implemented.       |
| 5\. Shareable timetable export     | Core               | Export the approved timetable as CSV. Printable HTML or PDF may be added if time permits.                                                                                                 |
| 6\. Alternative time suggestions   | Core               | When a requested slot conflicts, list candidate slots that satisfy participant, venue, duration, and buffer rules, with a reason for each suggestion.                                     |
| 7\. Venue availability checker     | Core               | Prevent overlapping use of a venue. Add a configurable 25- or 30-minute buffer after a session. Default: 30 minutes. Warn/block a next session that starts before the buffer has elapsed. |
| 8\. Event analytics dashboard      | Stretch            | Show total events, events per day, participant conflicts, venue conflicts, assigned/unassigned events, venue usage, and slot usage. A simple text/table dashboard is enough.              |
| 9\. Manual timetable adjustment    | Core               | Allow organisers to change event time or venue. Recheck constraints immediately and show warnings/errors before accepting the change.                                                     |
| 10\. Schedule validation report    | Core               | Check participant clashes, venue overlaps, insufficient buffers, missing scheduling data, and unassigned events. Explain each issue.                                                      |

# 5. Primary MFCS Concept: Graph Coloring

Graph coloring is the primary concept because the main problem is assigning time slots to events while ensuring that conflicting events do not happen simultaneously.

## 5.1 Mathematical model

- Represent each event as a vertex in a graph G = (V, E).
- V is the set of events.
- An edge (u, v) connects events that cannot be conducted at the same time. In the first version, this means they share at least one registered participant.
- A color represents a candidate time slot.
- A valid coloring assigns different colors to adjacent vertices; therefore, connected events receive different time slots.

Example: A = {S1, S2, S3}, B = {S3, S4}, and C = {S5, S6}. A and B share S3, so an edge connects A and B. C has no participant-conflict edge with either. A and B must receive different time slots.

## 5.2 Supporting MFCS concept: Set Theory

Store each event's participant IDs as a Python set. The intersection of two participant sets returns the students registered for both events. If the intersection is non-empty, the events share participants; a scheduling clash exists if their time intervals overlap.

Mathematical notation: Participants(A) ∩ Participants(B). Python idea: shared_students = participants_A.intersection(participants_B).

## 5.3 Honest algorithm limitation

Greedy graph coloring is beginner-friendly and can produce a valid schedule for the constraints it checks, but it does not guarantee the minimum possible number of time slots for every graph. Describe the result as a valid greedy schedule after validation, not as a mathematically optimal timetable.

# 6. Scheduling and Priority Rules

## 6.1 Participant conflict

Two events have a participant clash when they share one or more student IDs AND their scheduled time intervals overlap. Shared participants alone do not make a schedule invalid when the events occur at different times.

## 6.2 Conflict-based priority

Calculate each event's degree: the number of other events connected to it in the conflict graph. Process higher-degree events first because they have fewer safe choices. Break ties consistently, for example by larger participant count and then event ID/input order. This is a scheduling-difficulty heuristic, not a measure of institutional importance.

## 6.3 Optional greedy timetable generation

1. Build the conflict graph from participant overlaps.
2. Calculate each event's degree.
3. Sort events by descending degree.
4. For each event, find the first candidate slot that does not match the slot of any already-assigned neighbour.
5. Check venue availability and buffer rules before assigning the slot.
6. If no candidate slot is valid, leave the event unassigned and explain the blocking constraint.

Use a fixed list of organiser-defined candidate slots in the first version. This is simpler than generating arbitrary start times.

# 7. Venue Availability and 25–30 Minute Buffer

Treat a venue as occupied from the event start until the event end plus the configured buffer. Set the default buffer to 30 minutes and allow the organiser to choose 25 or 30 minutes.

Example: A session in Room A ends at 11:00. With a 30-minute buffer, Room A should not be considered available for another session before 11:30. A proposed 11:15 start must trigger a clear warning and must not be marked as safely available.

Distinguish two cases: (1) venue time intervals overlap — a hard venue conflict; (2) the next session starts after the previous event ends but before the buffer expires — a buffer violation/warning. Recommended default: block automatic assignment and show a warning for manual proposals. Make the buffer configurable because room reset and movement needs can vary.

# 8. Alternative Time Suggestions

- Search only candidate slots within the event date and preferred time window, when supplied.
- Check participant conflicts, venue occupancy, event duration, and the configured buffer.
- Show a short reason beside each suggestion, such as 'No shared-participant clash' or 'Venue available with 30-minute buffer'.
- If no slot is valid, say so and identify the constraint preventing assignment.
- Do not claim a time is best for student attendance unless student availability/preference data is actually collected.

# 9. Inputs, Outputs, and Data Model

## 9.1 Minimum event fields

| **Field**             | **Example**            | **Purpose**                                |
| --------------------- | ---------------------- | ------------------------------------------ |
| event_id              | EVT001                 | Unique identifier                          |
| event_name            | Python Workshop        | Readable name                              |
| date                  | 2026-12-05             | Event date                                 |
| start_time / end_time | 10:00 / 11:00          | Scheduled interval                         |
| participants          | S101, S102, S103       | Participant IDs; store internally as a set |
| venue                 | Lab 2                  | Required venue                             |
| preferred_window      | 09:00–13:00            | Optional organiser preference              |
| status                | Scheduled / Unassigned | Scheduling state                           |

## 9.2 Expected outputs

- Event list and scheduling status.
- Participant-conflict report with shared student IDs.
- Conflict-based priority ranking.
- Alternative time slots with reasons.
- Venue availability and buffer warnings.
- Timetable showing event, date, time, venue, and status.
- Analytics summary and schedule validation report.
- CSV export of the approved timetable.

# 10. Recommended Python Implementation

Use Python 3. A command-line menu is recommended for the first version. A graphical interface is optional and should only be attempted after the scheduling logic works.

| **Part**        | **Recommended choice**                                |
| --------------- | ----------------------------------------------------- |
| Language        | Python 3                                              |
| Data structures | Dictionary, list, set, tuple                          |
| Time handling   | datetime and timedelta (standard library)             |
| Storage         | JSON or CSV first; SQLite can be a later improvement  |
| Export          | csv module; optional HTML/PDF later                   |
| Interface       | Command-line menu first; Tkinter only if time remains |
| Testing         | unittest or repeatable manual test cases              |

## 10.1 Suggested modules

| **File**             | **Responsibility**                              |
| -------------------- | ----------------------------------------------- |
| main.py              | Menu and program flow                           |
| event_manager.py     | Add/edit/delete/list and load/save events       |
| conflict_detector.py | Set intersections, time overlap, conflict graph |
| priority.py          | Conflict degree and ranking                     |
| scheduler.py         | Optional greedy graph-coloring scheduler        |
| venue_checker.py     | Venue overlap and buffer checks                 |
| suggestions.py       | Alternative candidate slots                     |
| validator.py         | Full timetable validation and report            |
| analytics.py         | Summary statistics                              |
| exporter.py          | CSV timetable export                            |
| data/                | Sample and saved event data                     |

These are suggested separations, not a requirement to create every file immediately. Start with fewer files if necessary, then split the code into modules as it grows.

# 11. Reliability, Validation, and Limitations

## 11.1 What it can check

- Whether participant sets share student IDs.
- Whether scheduled time intervals overlap.
- Whether the same venue is reused too soon, including the configured buffer.
- Whether connected events have different assigned slots.
- Whether required scheduling information is missing.
- Whether the timetable passes the implemented validation rules.

## 11.2 What it cannot guarantee

- Greedy graph coloring does not guarantee the globally optimal timetable or minimum number of slots.
- Student convenience cannot be inferred unless student availability is collected.
- Conflict degree does not measure an event's real-world importance.
- Travel time between distant venues is not considered unless explicitly implemented.
- The system cannot guarantee participant lists are complete or correct; organisers must maintain accurate registration data.

Reliability depends on accurate input, correct time validation, and a final validation pass. Never silently accept an invalid schedule. Show the event pair, venue, time, or rule responsible for each issue.

# 12. Testing Plan

| **Test**              | **Situation**                                     | **Expected result**                         |
| --------------------- | ------------------------------------------------- | ------------------------------------------- |
| Shared participant    | A={S1,S2}; B={S2,S3}; times overlap               | Report clash and show S2                    |
| No shared participant | A={S1}; B={S2}; times overlap                     | No participant clash                        |
| Different times       | Same student in two events at different times     | No simultaneous clash                       |
| Venue overlap         | Room 1 used 10:00–11:00 and 10:30–11:30           | Venue conflict                              |
| Buffer respected      | Previous ends 11:00; next starts 11:30; buffer 30 | Accepted                                    |
| Buffer too short      | Previous ends 11:00; next starts 11:20; buffer 30 | Warning/constraint violation                |
| Graph coloring        | Two connected events are auto-scheduled           | Different slots, if feature enabled         |
| Manual edit           | Move event into conflicting slot                  | Warn and reject or require correction       |
| No valid slot         | All candidate slots violate a constraint          | Leave unassigned and explain why            |
| CSV export            | Export a validated timetable                      | Correct event/date/time/venue/status fields |

# 13. Development Plan

| **Stage**                      | **Build**                               | **Completion condition**                              |
| ------------------------------ | --------------------------------------- | ----------------------------------------------------- |
| 1\. Data foundation            | Event structure; add/list/edit/delete   | Events can be entered and saved                       |
| 2\. Conflict detection         | Set intersection and time overlap       | Correct conflict pairs and shared IDs shown           |
| 3\. Venue rules                | Venue overlap and 25–30 min buffer      | Overlaps and buffer violations detected               |
| 4\. Priority                   | Conflict degree and sorting             | Consistent ranking produced                           |
| 5\. Manual scheduling          | Assign/change time and venue            | Manual timetable can be checked                       |
| 6\. Validation and suggestions | Whole-schedule report and alternatives  | Issues explained; valid alternatives listed           |
| 7\. Export and analytics       | CSV export and summary dashboard        | Timetable can be inspected and shared                 |
| 8\. Optional auto-scheduler    | Greedy graph coloring plus venue checks | Valid assignments generated for supported constraints |

Recommended minimum viable project: complete stages 1–7. Stage 8 is a stretch goal. This keeps the project demonstrable even if automatic timetable generation takes longer than expected.

# 14. Suggested Demonstration Flow

7. Add three or four sample events with participant IDs, duration, preferred window, and venue.
8. Run conflict detection and show shared students.
9. Display conflict-based priority ranking.
10. Assign an event manually and demonstrate a participant or venue clash.
11. Demonstrate the 30-minute venue-buffer warning.
12. Show alternative time suggestions.
13. Run schedule validation and explain any remaining issues.
14. If implemented, run automatic timetable generation and explain graph coloring.
15. Display analytics and export the final timetable to CSV.

# 15. MFCS Viva Explanation

The primary concept used in this project is graph coloring. Each college event is a vertex. If two events share registered students, an edge connects them because they should not happen at the same time. A color represents a time slot. Assigning different colors to connected vertices creates a schedule without those participant clashes. Sets and set intersection identify common participants. A greedy coloring algorithm can generate a valid schedule for the constraints it checks, but it does not always use the minimum possible number of slots.

# 16. Instructions for Another LLM or Developer

Treat this specification as the source of truth when helping implement the project.

- Do not turn this into an AI/ML project. The first version is a transparent, rule-based Python application.
- Keep Graph Coloring as the primary MFCS concept and Set Intersection as supporting concept.
- Prioritise beginner-readable code, clear names, comments, and small functions.
- Implement the minimum viable project before optional features.
- Automatic timetable generation is optional; preserve manual scheduling and validation if it is not implemented.
- Use a configurable 25- or 30-minute venue buffer, defaulting to 30 minutes.
- Distinguish participant conflicts, venue overlaps, and venue-buffer warnings.
- Do not describe conflict degree as event importance.
- Do not claim greedy graph coloring always finds the minimum number of slots.
- Provide sample data, expected output, tests, and a README.
- Do not silently ignore invalid data or constraints; explain validation failures.

# 17. Final Feasibility Assessment

| **Feature area**               | **Difficulty** | **Reason**                                                         |
| ------------------------------ | -------------- | ------------------------------------------------------------------ |
| Event management               | Easy           | Basic Python data structures and file handling                     |
| Participant conflict detection | Easy           | Set intersection and interval comparison                           |
| Priority ranking               | Easy           | Count graph neighbours and sort                                    |
| Venue checker + buffer         | Easy–Moderate  | Time interval checks with timedelta                                |
| Manual adjustment + validation | Moderate       | Must rerun consistent checks after changes                         |
| Alternative suggestions        | Moderate       | Filter candidate slots against constraints                         |
| CSV export + basic analytics   | Easy           | Python standard library                                            |
| Automatic graph coloring       | Moderate       | Greedy algorithm is manageable; integrating constraints adds work  |
| Polished GUI/PDF               | Stretch        | Can consume time without strengthening the core MFCS demonstration |

**Overall recommendation:** This project is feasible for a beginner if built in stages. Complete event management, conflict detection, venue-buffer checks, manual scheduling, validation, alternatives, analytics, and CSV export first. Add greedy graph-coloring automation only after these foundations work. Confirm the topic/concept combination with faculty before implementation because the assignment requires topic approval and may restrict duplicates.