#!/bin/zsh
# Bootstrap the dev environment: venv + deps (idempotent).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  echo "creating .venv..."
  /opt/homebrew/bin/python3 -m venv .venv 2>/dev/null || python3 -m venv .venv
fi

.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt -e .
echo "OK. Activate with: source .venv/bin/activate"
echo "Run:               python -m presence.aggregator --simulator --print"
