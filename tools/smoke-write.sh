#!/usr/bin/env bash
# Проверка записи: то, что UI отправляет при создании/правке/удалении.
set -uo pipefail
BASE=http://127.0.0.1:8000/api
JAR=$(mktemp)
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36'
LOGIN=demo; DOMAIN=budgettracker.local; PASS=demo12345

curl -s -o /dev/null -b "$JAR" -c "$JAR" -A "$UA" -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$LOGIN@$DOMAIN" --data-urlencode "password=$PASS"

call() { # метод путь тело
  local method=$1 path=$2 body=${3:-}
  if [ -n "$body" ]; then
    curl -s -o /tmp/w.json -w '%{http_code}' -b "$JAR" -c "$JAR" -A "$UA" -X "$method" \
      -H 'Content-Type: application/json' -d "$body" "$BASE$path"
  else
    curl -s -o /tmp/w.json -w '%{http_code}' -b "$JAR" -c "$JAR" -A "$UA" -X "$method" "$BASE$path"
  fi
}
say() {
  printf '%-44s %s\n' "$1" "$2"
  case "$2" in
    2*) ;;
    *) printf '    тело: %s\n' "$(head -c 300 /tmp/w.json)" ;;
  esac
}

ACC=$(curl -s -b "$JAR" -A "$UA" "$BASE/finance/accounts/" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[0]["id"], d[0]["currency_id"])')
ACCOUNT=${ACC% *}; CCY=${ACC#* }
CAT=$(curl -s -b "$JAR" -A "$UA" "$BASE/finance/categories/" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(next(c["id"] for c in d if c["type"]=="expense"))')
say "счёт / валюта / категория" "$ACCOUNT $CCY $CAT"

BODY=$(python3 -c "
import json,datetime
print(json.dumps({'account_id': $ACCOUNT, 'category_id': $CAT, 'amount': 12.5, 'currency_id': '$CCY',
 'type':'expense','date': datetime.datetime.now().replace(microsecond=0).isoformat(), 'note':'smoke-test','tag_ids':[]}))")
say "POST /finance/transactions/" "$(call POST /finance/transactions/ "$BODY")"
TX=$(python3 -c 'import json;print(json.load(open("/tmp/w.json"))["id"])')

say "PATCH /finance/transactions/{id}" "$(call PATCH "/finance/transactions/$TX" '{"amount": 33.25, "note":"smoke-updated"}')"
say "GET /finance/transactions/{id}" "$(call GET "/finance/transactions/$TX")"

say "POST /finance/tags/" "$(call POST /finance/tags/ '{"name":"smoke-tag","color":"#3aa76d"}')"
TAG=$(python3 -c 'import json;print(json.load(open("/tmp/w.json"))["id"])')
say "PUT /finance/tags/{id}" "$(call PUT "/finance/tags/$TAG" '{"name":"smoke-tag-2"}')"

say "POST /finance/templates/" "$(call POST /finance/templates/ "{\"name\":\"smoke-tpl\",\"type\":\"expense\",\"amount\":10,\"currency_id\":\"$CCY\",\"account_id\":$ACCOUNT,\"category_id\":$CAT}")"
TPL=$(python3 -c 'import json;print(json.load(open("/tmp/w.json"))["id"])')
say "POST /finance/templates/{id}/apply" "$(call POST "/finance/templates/$TPL/apply")"

say "POST /finance/rules/" "$(call POST /finance/rules/ "{\"name\":\"smoke-rule\",\"field\":\"note\",\"operator\":\"contains\",\"value\":\"smoke\",\"set_category_id\":$CAT,\"is_active\":true}")"
RULE=$(python3 -c 'import json;print(json.load(open("/tmp/w.json"))["id"])')
say "POST /finance/rules/apply?dry_run=true" "$(call POST '/finance/rules/apply?dry_run=true' '{}')"

say "PUT /finance/currencies/USD/rate" "$(call PUT /finance/currencies/USD/rate '{"rate": 3.11}')"
say "DELETE /finance/currencies/USD/rate" "$(call DELETE /finance/currencies/USD/rate)"

say "POST /billing/subscription (mock)" "$(call POST /billing/subscription '{"plan_code":"monthly","provider":"mock"}')"
say "GET /billing/subscription" "$(call GET /billing/subscription)"
say "POST /billing/payment-methods" "$(call POST /billing/payment-methods '{"kind":"card","provider":"mock","token":"tok_4242","make_default":true}')"
PM=$(python3 -c 'import json;d=json.load(open("/tmp/w.json"));print(d.get("id",""))' 2>/dev/null || echo '')
[ -n "$PM" ] && say "DELETE /billing/payment-methods/{id}" "$(call DELETE "/billing/payment-methods/$PM")"

say "PATCH /users/me" "$(call PATCH /users/me '{"timezone":"Europe/Moscow"}')"

say "DELETE /finance/transactions/{id}" "$(call DELETE "/finance/transactions/$TX")"
say "DELETE /finance/rules/{id}" "$(call DELETE "/finance/rules/$RULE")"
say "DELETE /finance/templates/{id}" "$(call DELETE "/finance/templates/$TPL")"
say "DELETE /finance/tags/{id}" "$(call DELETE "/finance/tags/$TAG")"
rm -f "$JAR"
