#!/bin/bash
# Captures screens in real WebKit (WKWebView, the Safari engine) — fallback check.
set -u
export PATH=/usr/local/bin:$PATH
export HOME="$(cd "$(dirname "$0")/.." && pwd)/tools/home"
cd "$(dirname "$0")/.." || exit 1

BASE="http://127.0.0.1:5199"
OUT="docs/design/mockups/webkit"
mkdir -p "$OUT"

shoot() { # name path width height
  swift -module-cache-path ./tools/.mcache tools/webkit-shot.swift \
    "$BASE$2" "$OUT/$1.png" "$3" "$4" 2>&1 | grep -E "^OK|error|timeout|failed"
}

for entry in dashboard:/ records:/records accounts:/accounts analytics:/analytics settings:/settings login:/login; do
  name=${entry%%:*}
  path=${entry#*:}
  for theme in dark light; do
    shoot "${name}-desktop-${theme}" "${path}?theme=${theme}" 1440 900
  done
  shoot "${name}-mobile-dark" "${path}?theme=dark" 390 844
done

# Fallback self-check: the "Refraction (Chromium)" card must show the fallback
shoot "design-desktop-dark" "/design?theme=dark" 1440 900

echo "WEBKIT DONE"
ls -1 "$OUT" | wc -l
