"""Simple portfolio server — run from any terminal.

Usage:
    python serve.py

Then open http://localhost:8000 in any browser.
Works from a USB stick too — just run from whatever folder this is in.
"""
import http.server
import socketserver
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

os.chdir(DIRECTORY)

Handler = http.server.SimpleHTTPRequestHandler

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"\n  Portfolio running at http://localhost:{PORT}")
    print(f"  Serving from: {DIRECTORY}")
    print(f"  Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
