#!/usr/bin/env bash
# Build script for Render - installs system dependencies needed by scipy/opencv

set -e

# Install system dependencies for OpenCV and scipy
apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
