#!/usr/bin/env python3
"""Start the InfraGuard frontend dev server as a persistent daemon."""
import subprocess, os

frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')

subprocess.Popen(
    ['npx', 'vite', '--host', '127.0.0.1', '--port', '5173'],
    cwd=frontend_dir,
    stdout=open('/tmp/ig_frontend.log', 'w'),
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
print("InfraGuard frontend launched on http://127.0.0.1:5173")
