"""The HTTP server used by the College Event Planning Assistant."""

import io
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from web.planner import EventPlanner


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
STATIC_FOLDER = Path(__file__).resolve().parent / "static"
DATA_FILE = Path(os.environ.get(
    "EVENT_PLANNER_DATA_FILE",
    PROJECT_FOLDER / "data" / "events.json",
))
planner = EventPlanner(DATA_FILE)


class EventPlannerHandler(BaseHTTPRequestHandler):
    """Translate browser requests into planner actions."""

    def request_path(self):
        """Return the URL path without its query string."""
        return urlsplit(self.path).path

    def query_params(self):
        """Return parsed query parameters dictionary."""
        return parse_qs(urlsplit(self.path).query)

    def do_GET(self):
        """Serve the page and read-only API addresses."""
        path = self.request_path()
        params = self.query_params()

        static_files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/static/style.css": ("style.css", "text/css; charset=utf-8"),
            "/static/app.js": ("app.js", "application/javascript; charset=utf-8"),
        }

        if path in static_files:
            filename, content_type = static_files[path]
            self.send_static_file(filename, content_type)
        elif path == "/api/events":
            self.send_json({"events": planner.list_events()})
        elif path.startswith("/api/events/") and path.endswith("/suggestions"):
            # format: /api/events/<event_id>/suggestions
            event_id = path[len("/api/events/"):-len("/suggestions")]
            data = planner.suggest_slots(unquote(event_id))
            status = 200 if "error" not in data else 404
            self.send_json(data, status=status)
        elif path.startswith("/api/events/"):
            event_id = path[len("/api/events/"):]
            event = planner.get_event(unquote(event_id))
            if event:
                self.send_json({"event": event})
            else:
                self.send_json({"message": "Event not found."}, status=404)
        elif path == "/api/suggestions":
            event_id = params.get("event_id", [""])[0]
            if not event_id:
                self.send_json({"message": "Query parameter event_id is required."}, status=400)
                return
            data = planner.suggest_slots(event_id)
            status = 200 if "error" not in data else 404
            self.send_json(data, status=status)
        elif path == "/api/conflicts":
            self.send_json(planner.find_conflicts())
        elif path == "/api/priority":
            self.send_json({"ranking": planner.get_priority_ranking()})
        elif path == "/api/validation":
            self.send_json(planner.validate_schedule())
        elif path == "/api/analytics":
            self.send_json(planner.get_analytics())
        elif path == "/api/buffer":
            self.send_json({"venue_buffer": planner.get_venue_buffer()})
        elif path == "/api/export":
            self.send_csv()
        else:
            self.send_json({"message": "Endpoint not found."}, status=404)

    def do_POST(self):
        """Handle requests that add, replace, schedule, or configure events."""
        path = self.request_path()

        if path == "/api/events":
            details = self.read_json()
            if details is None:
                return
            result = planner.add_event(details)
            success, message = result[0], result[1]
            event_id = result[2] if len(result) > 2 else None
            warnings = result[3] if len(result) > 3 else []
            status = 201 if success else 400
            self.send_json({"success": success, "message": message,
                            "event_id": event_id, "warnings": warnings}, status)
        elif path == "/api/samples":
            count = planner.load_sample_events()
            self.send_json({
                "success": True,
                "message": f"{count} standard sample events loaded successfully.",
            })
        elif path == "/api/schedule":
            result = planner.create_schedule()
            self.send_json({"success": True, **result})
        elif path == "/api/buffer":
            data = self.read_json()
            if data is None:
                return
            buffer_val = data.get("buffer") or data.get("venue_buffer")
            success, message = planner.set_venue_buffer(buffer_val)
            status = 200 if success else 400
            self.send_json({"success": success, "message": message, "venue_buffer": planner.get_venue_buffer()}, status)
        else:
            self.send_json({"message": "Endpoint not found."}, status=404)

    def do_PUT(self):
        """Handle requests to edit/adjust existing event details or timetable assignments."""
        path = self.request_path()
        prefix = "/api/events/"

        if path.startswith(prefix):
            event_id = path[len(prefix):]
            if not event_id:
                self.send_json({"message": "Event ID required."}, status=400)
                return

            details = self.read_json()
            if details is None:
                return

            success, message, warnings = planner.update_event(unquote(event_id), details)
            status = 200 if success else 400
            self.send_json({
                "success": success,
                "message": message,
                "warnings": warnings,
            }, status)
        else:
            self.send_json({"message": "Endpoint not found."}, status=404)

    def do_DELETE(self):
        """Handle a delete request containing an event ID in the URL."""
        prefix = "/api/events/"
        path = self.request_path()
        event_id = path[len(prefix):] if path.startswith(prefix) else ""

        if not event_id:
            self.send_json({"message": "Event ID required."}, status=400)
            return

        success, message = planner.delete_event(unquote(event_id).upper())
        status = 200 if success else 404
        self.send_json({"success": success, "message": message}, status)

    def read_json(self):
        """Read and validate a JSON request body."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self.send_json({"message": "Request data must use valid JSON."}, status=400)
            return None

        if not isinstance(data, dict):
            self.send_json({"message": "Request data must be a JSON object."}, status=400)
            return None
        return data

    def send_static_file(self, filename, content_type):
        """Read one public file from web/static and send it to the browser."""
        file_path = STATIC_FOLDER / filename
        if not file_path.exists():
            self.send_json({"message": "File not found."}, status=404)
            return
        self.send_bytes(
            file_path.read_bytes(),
            content_type,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    def send_json(self, data, status=200):
        encoded = json.dumps(data).encode("utf-8")
        self.send_bytes(encoded, "application/json; charset=utf-8", status)

    def send_bytes(self, data, content_type, status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def send_csv(self):
        csv_text = planner.export_csv_data()
        self.send_bytes(
            csv_text.encode("utf-8"),
            "text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=event_timetable.csv"},
        )

    def log_message(self, *_):
        """Keep normal request logs out of the terminal."""
        return


def start_server():
    """Start the website on localhost:8000."""
    try:
        server = ThreadingHTTPServer(("localhost", 8000), EventPlannerHandler)
    except OSError:
        print("Port 8000 is already in use.")
        return

    print("Smart College Event Planning Assistant is running at http://localhost:8000")
    print(f"Venue buffer configured to: {planner.get_venue_buffer()} minutes")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
