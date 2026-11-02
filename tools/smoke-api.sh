#!/usr/bin/env bash
# Сквозная проверка API так, как его вызывает фронтенд.
set -uo pipefail
BASE=http://127.0.0.1:8000/api
JAR=$(mktemp)
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36'
LOGIN=demo
DOMAIN=budgettracker.local
PASS=demo12345

code() { curl -s -o /tmp/smoke-body.json -w '%{http_code}' -b "$JAR" -c "$JAR" -A "$UA" "$@"; }
say() { printf '%-46s %s\n' "$1" "$2"; }

say "POST /auth/login" "$(code -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$LOGIN@$DOMAIN" --data-urlencode "password=$PASS")"
TOKEN_OK=$(grep -c access_token "$JAR" || true)
say "cookies в jar" "$TOKEN_OK"

say "GET /users/me" "$(code "$BASE/users/me")"
say "GET /finance/accounts/" "$(code "$BASE/finance/accounts/")"
say "GET /finance/accounts/balance" "$(code "$BASE/finance/accounts/balance")"
say "GET /finance/categories/tree" "$(code "$BASE/finance/categories/tree")"
say "GET /finance/tags/" "$(code "$BASE/finance/tags/")"
say "GET /finance/templates/" "$(code "$BASE/finance/templates/")"
say "GET /finance/rules/" "$(code "$BASE/finance/rules/")"
say "GET /finance/currencies/rates" "$(code "$BASE/finance/currencies/rates")"
say "GET /finance/transactions/?with_total=true" "$(code "$BASE/finance/transactions/?with_total=true&limit=5")"
TOTAL=$(curl -s -D /tmp/smoke-head.txt -o /tmp/smoke-body.json -b "$JAR" -A "$UA" "$BASE/finance/transactions/?with_total=true&limit=5" >/dev/null; grep -i '^x-total-count' /tmp/smoke-head.txt | tr -d '\r' | awk '{print $2}')
say "X-Total-Count записей" "${TOTAL:-нет}"

say "GET /analytics/summary" "$(code "$BASE/analytics/summary")"
say "GET /analytics/timeseries?metric=balance" "$(code "$BASE/analytics/timeseries?metric=balance&group_by=day")"
say "GET /analytics/timeseries?metric=cashflow" "$(code "$BASE/analytics/timeseries?metric=cashflow&group_by=week")"
say "GET /analytics/by-category" "$(code "$BASE/analytics/by-category?transaction_type=expense")"
say "GET /analytics/by-account" "$(code "$BASE/analytics/by-account")"
say "GET /analytics/matrix?months=6" "$(code "$BASE/analytics/matrix?months=6&transaction_type=expense&rollup=true")"

say "GET /billing/plans" "$(code "$BASE/billing/plans")"
say "GET /billing/providers" "$(code "$BASE/billing/providers")"
say "GET /billing/subscription" "$(code "$BASE/billing/subscription")"
say "GET /billing/payment-methods" "$(code "$BASE/billing/payment-methods")"
say "GET /billing/payments" "$(code "$BASE/billing/payments?limit=5")"
say "GET /users/me/export" "$(code "$BASE/users/me/export")"
rm -f "$JAR"
