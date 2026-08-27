#!/usr/bin/env python3
"""Start the InfraGuard backend as a persistent daemon."""
import subprocess, sys, os

os.chdir(os.path.join(os.path.dirname(__file__), '..', 'backend'))
venv_python = os.path.join('venv', 'bin', 'python')

subprocess.Popen(
    [venv_python, '-m', 'uvicorn', 'app.main:app',
     '--host', '127.0.0.1', '--port', '8000'],
    stdout=open('/tmp/ig_backend.log', 'w'),
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
print("InfraGuard backend launched on http://127.0.0.1:8000")
