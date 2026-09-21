#!/bin/bash
# Run against the already deployed source tree; no database or existing service changes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${REHAB_PYTHON:-python3.12}"
"$PY" -c 'import sys; assert sys.version_info[:2] == (3,12), "Use Python 3.12 for the local reference"'
"$PY" -m venv "$ROOT/.vision-venv"
"$ROOT/.vision-venv/bin/python" -m pip install -r "$ROOT/deploy/requirements-rtmpose-server.txt"
"$ROOT/.vision-venv/bin/python" -m pip install --no-deps rtmlib==0.0.16
cd "$ROOT/algorithm/rehab-pose-demo"
"$ROOT/.vision-venv/bin/python" -c 'from pathlib import Path; from rehab_pose.model import download_rtmpose; download_rtmpose(Path("models/rtmpose"), "detected")'
"$ROOT/.vision-venv/bin/python" rtmpose_reference.py
echo 'Reference validated. Complete the RTMPOSE_ROLLOUT.md checklist before switching the service.'
