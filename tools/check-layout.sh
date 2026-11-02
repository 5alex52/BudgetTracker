#!/bin/bash
# Проверяет каждый экран на обрезанный контент (scrollWidth > clientWidth).
# Выводит строку OVERFLOW <экран> <ширина>: виновники, или ok.
set -u
export PATH=/usr/local/bin:$PATH
cd "$(dirname "$0")/.." || exit 1

BASE="http://127.0.0.1:5199"
PROBE='(() => {
  const out = [];
  document.querySelectorAll("body *").forEach((node) => {
    const style = getComputedStyle(node);
    if (style.position === "fixed") return;
    if (node.classList.contains("sr-only")) return;
    // SVG-текст не имеет clientWidth: сравнение для него бессмысленно
    if (node instanceof SVGElement) return;
    if (node.closest("[role=dialog]")) return;
    if (node.scrollWidth > node.clientWidth + 1 && node.clientWidth > 0) {
      const cls = String(node.className).split(" ").slice(0, 2).join(".");
      out.push(node.tagName.toLowerCase() + "." + cls + " sw=" + node.scrollWidth + "/cw=" + node.clientWidth);
    }
  });
  return "OVERFLOW " + (out.length ? out.slice(0, 3).join(" | ") : "ok");
})()'

for entry in dashboard:/ accounts:/accounts records:/records analytics:/analytics settings:/settings login:/login design:/design \
  settings-currencies:/settings/currencies settings-categories:/settings/categories settings-templates:/settings/templates \
  settings-tags:/settings/tags settings-payments:/settings/payments settings-rules:/settings/rules settings-privacy:/settings/privacy account-detail:/accounts/alfa; do
  name=${entry%%:*}
  path=${entry#*:}
  for width in 390 1440; do
    if [ "$width" = "390" ]; then height=844; else height=900; fi
    node tools/cdp-shot.mjs --url "$BASE${path}?theme=dark" --out /tmp/probe.png \
      --width "$width" --height "$height" --dpr 1 --theme dark \
      --actions "[{\"eval\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$PROBE")}]" 2>&1 \
      | grep -E "OVERFLOW|нет цели" | sed "s/^/[$name $width] /"
  done
done
echo "ПРОВЕРКА ЗАВЕРШЕНА"
