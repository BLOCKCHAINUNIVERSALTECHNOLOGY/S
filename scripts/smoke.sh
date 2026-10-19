#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "OS: $(uname -s) $(uname -m)"
echo "Python: $(python3 --version)"
python3 s version
python3 s doctor
python3 s test
python3 s new _smoke_app
python3 s run _smoke_app/main.s
python3 s check _smoke_app/main.s
echo "SMOKE OK"
