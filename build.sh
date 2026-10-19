#!/usr/bin/env bash
# Build the full S system
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
echo "=== S System Build ==="
echo "[1/4] Native Rust s_fast"
(cd native/s_fast && cargo build --release)
cp -f native/s_fast/target/release/s_fast /tmp/s_fast 2>/dev/null || true
chmod +x /tmp/s_fast native/s_fast/target/release/s_fast 2>/dev/null || true
mkdir -p bin
cp -f native/s_fast/target/release/s_fast bin/s_fast 2>/dev/null || true
echo "[2/4] Tests"
python3 s test
echo "[3/4] Doctor"
python3 s doctor
echo "[4/4] Static site sample"
python3 s html build examples/static_site/site.s --out=examples/static_site/out
echo "=== BUILD OK ==="
echo "Run site: python3 s serve examples/static_site/out --port=8080"
