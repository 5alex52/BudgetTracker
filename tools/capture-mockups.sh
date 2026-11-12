#!/bin/bash
# Captures the full mockup set: screen × theme × width + individual states.
# Requires a running dev server on 5199 and Node 22+.
set -u

export PATH=/usr/local/bin:$PATH
cd "$(dirname "$0")/.." || exit 1

BASE="http://127.0.0.1:5199"
OUT="docs/design/mockups"
mkdir -p "$OUT"

shot() { # name url width height theme extra-actions
  local name=$1 url=$2 width=$3 height=$4 theme=$5 actions=${6:-[]}
  node tools/cdp-shot.mjs \
    --url "$url" --out "$OUT/$name.png" \
    --width "$width" --height "$height" --dpr 1 \
    --theme "$theme" --full --actions "$actions" 2>&1 | tail -1
}

SCREENS="dashboard:/ accounts:/accounts records:/records analytics:/analytics settings:/settings login:/login design:/design"

for entry in $SCREENS; do
  name=${entry%%:*}
  path=${entry#*:}
  for theme in dark light; do
    shot "${name}-desktop-${theme}" "$BASE${path}?theme=${theme}" 1440 900 "$theme"
    shot "${name}-mobile-${theme}" "$BASE${path}?theme=${theme}" 390 844 "$theme"
  done
done

# States: the add-record modal (opened by the navbar button)
for theme in dark light; do
  shot "record-modal-desktop-${theme}" "$BASE/?theme=${theme}" 1440 900 "$theme" '[{"clickText":"Запись"},{"wait":700}]'
done

# States: filters in a Sheet on mobile
shot "records-filters-mobile-dark" "$BASE/records?theme=dark" 390 844 dark '[{"clickText":"Мой фильтр"},{"wait":700}]'

# States: the advanced-charts tab in analytics
shot "analytics-advanced-desktop-dark" "$BASE/analytics?theme=dark" 1440 900 dark '[{"clickText":"Продвинутые"},{"wait":500}]'

echo "DONE"
ls -1 "$OUT" | wc -l
