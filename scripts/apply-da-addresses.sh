#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/scripts/apply_da_addresses.py"
