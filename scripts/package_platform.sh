#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-linux-x86_64}"
OUT="$ROOT/dist/platforms/$TAG"
rm -rf "$OUT"
mkdir -p "$OUT/bin" "$OUT/lib/s-lang"

# Copy selected paths only (avoid recursion into dist)
for item in s src examples docs website hub studio scripts LICENSE README.md \
  CHANGELOG.md CONTRIBUTING.md SECURITY.md CODE_OF_CONDUCT.md COMMUNITY.md \
  PRIVACY.md SUPPORT.md ROADMAP.md VERSION install.sh build.sh project.se s.lock \
  native/s_fast/Cargo.toml native/s_fast/src; do
  if [[ -e "$ROOT/$item" ]]; then
    mkdir -p "$OUT/lib/s-lang/$(dirname "$item")"
    cp -a "$ROOT/$item" "$OUT/lib/s-lang/$item"
  fi
done

# Native binary for linux host builds
if [[ -f "$ROOT/native/s_fast/target/release/s_fast" ]]; then
  if [[ "$TAG" == linux* ]]; then
    cp -f "$ROOT/native/s_fast/target/release/s_fast" "$OUT/bin/s_fast"
    chmod +x "$OUT/bin/s_fast" 2>/dev/null || true
  fi
fi

cat > "$OUT/bin/s" << 'WRAP'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$DIR/bin:$PATH"
export S_FAST="${S_FAST:-$DIR/bin/s_fast}"
exec python3 "$DIR/lib/s-lang/s" "$@"
WRAP
chmod +x "$OUT/bin/s"

if [[ "$TAG" == windows* ]]; then
  cat > "$OUT/bin/s.bat" << 'BAT'
@echo off
set DIR=%~dp0..
python "%DIR%\lib\s-lang\s" %*
BAT
fi

cat > "$OUT/README.txt" << R
S Language portable — $TAG
Requires Python 3.10+

  export PATH="\$PWD/bin:\$PATH"   # Unix
  s version

Windows: bin\\s.bat version
R

(cd "$ROOT/dist/platforms" && tar -czf "${TAG}.tar.gz" "$TAG")
ls -lh "$ROOT/dist/platforms/${TAG}.tar.gz"
echo "OK $TAG"
