"""Preview the built site at http://localhost:8642 (Ctrl+C to stop)."""
import functools
import http.server
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
PORT = 8642
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
print(f"Previewing {DOCS} at http://localhost:{PORT}/")
http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler).serve_forever()
