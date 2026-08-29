"""Vercel serverless entry point for FastAPI backend.

This file allows Vercel to run the FastAPI app as a serverless function.
The app is imported from the main module and exposed for Vercel's Python runtime.
"""
import os
import sys

# Ensure the backend directory is in the path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_current_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Import the FastAPI app
from app.main import app

# Vercel expects the app to be importable as 'app'
