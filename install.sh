#!/usr/bin/env bash
# S Language — one-command install (Wave 1)
set -euo pipefail
PREFIX="${PREFIX:-$HOME/.local}"
ROOT="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$PREFIX/bin" "$PREFIX/lib/s-lang"
# Copy project tree for offline use
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
    "$ROOT/" "$PREFIX/lib/s-lang/"
else
  cp -a "$ROOT/." "$PREFIX/lib/s-lang/"
  find "$PREFIX/lib/s-lang" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
fi

cat > "$PREFIX/bin/s" << WRAP
#!/usr/bin/env bash
exec python3 "$PREFIX/lib/s-lang/s" "\$@"
WRAP
chmod +x "$PREFIX/bin/s" "$PREFIX/lib/s-lang/s" 2>/dev/null || true

echo "S Language installed."
echo "  binary: $PREFIX/bin/s"
echo "  Add to PATH if needed: export PATH=\"$PREFIX/bin:\$PATH\""
echo "  Try: s version && s new hello && s run hello/main.s"
