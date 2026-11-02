#!/usr/bin/env python3
"""Сквозная проверка записи: payload'ы ровно те, что отправляет фронтенд.

Запуск: python3 tools/smoke_write.py
Требует поднятый backend на 127.0.0.1:8000 и демо-данные (scripts.seed_demo).
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from http.cookiejar import CookieJar

BASE = "http://127.0.0.1:8000/api"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
LOGIN = "demo"
DOMAIN = "budgettracker.local"
PASSWORD = "demo12345"

jar = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
results: list[tuple[str, int]] = []


def call(method: str, path: str, body: dict | None = None, form: dict | None = None):
    url = f"{BASE}{path}"
    data = None
    headers = {"User-Agent": UA}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(request) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:  # 4xx/5xx — тоже результат проверки
        raw = error.read()
        status = error.code
    payload = None
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw[:200].decode(errors="replace")
    results.append((f"{method} {path}", status))
    marker = "ok " if 200 <= status < 300 else "!! "
    print(f"{marker}{method:6} {path:46} {status}")
    if status >= 400:
        print(f"     тело: {str(payload)[:300]}")
    return payload


def main() -> int:
    login = call(
        "POST",
        "/auth/login",
        form={"username": f"{LOGIN}@{DOMAIN}", "password": PASSWORD},
    )
    if not login:
        print("логин не удался — проверьте, что демо-данные засеяны")
        return 1

    accounts = call("GET", "/finance/accounts/") or []
    account = accounts[0]
    account_id, currency = account["id"], account["currency_id"]
    categories = call("GET", "/finance/categories/") or []
    category_id = next(item["id"] for item in categories if item["type"] == "expense")

    # --- запись: создание, правка, чтение, удаление
    record = call(
        "POST",
        "/finance/transactions/",
        {
            "account_id": account_id,
            "category_id": category_id,
            "amount": 12.5,
            "currency_id": currency,
            "type": "expense",
            "date": datetime.now().replace(microsecond=0).isoformat(),
            "note": "smoke-test",
            "tag_ids": [],
        },
    )
    transaction_id = record["id"]
    call("PATCH", f"/finance/transactions/{transaction_id}", {"amount": 33.25, "note": "smoke-updated"})
    call("GET", f"/finance/transactions/{transaction_id}")

    # --- метки
    tag = call("POST", "/finance/tags/", {"name": "smoke-tag", "color": "#3aa76d"})
    tag_id = tag["id"]
    call("PATCH", f"/finance/tags/{tag_id}", {"name": "smoke-tag-2"})

    # --- шаблоны: создание и применение
    template = call(
        "POST",
        "/finance/templates/",
        {
            "name": "smoke-template",
            "type": "expense",
            "amount": 10,
            "currency_id": currency,
            "account_id": account_id,
            "category_id": category_id,
            "note": None,
            "tag_ids": [],
        },
    )
    template_id = template["id"] if isinstance(template, dict) and "id" in template else None
    applied_id = None
    if template_id:
        applied = call("POST", f"/finance/templates/{template_id}/apply")
        # Шаблон создаёт настоящую запись — её тоже нужно убрать за собой
        if isinstance(applied, dict) and applied.get("id"):
            applied_id = applied["id"]

    # --- правила: создание, прогон, переключение
    rule = call(
        "POST",
        "/finance/rules/",
        {
            "name": "smoke-rule",
            "field": "note",
            "operator": "contains",
            "value": "smoke",
            "set_category_id": category_id,
            "add_tag_id": None,
            "exclude_from_statistics": False,
            "is_active": True,
        },
    )
    rule_id = rule["id"] if isinstance(rule, dict) and "id" in rule else None
    call("POST", "/finance/rules/apply?dry_run=true", {})
    if rule_id:
        call("PATCH", f"/finance/rules/{rule_id}", {"is_active": False})

    # --- личный курс валюты
    call("PUT", "/finance/currencies/USD/rate", {"rate": 3.11})
    call("DELETE", "/finance/currencies/USD/rate")

    # --- массовое удаление и серверная выгрузка (кнопки на экране «Записи»)
    extra = call(
        "POST",
        "/finance/transactions/",
        {
            "account_id": account_id,
            "category_id": category_id,
            "amount": 1.0,
            "currency_id": currency,
            "type": "expense",
            "date": datetime.now().replace(microsecond=0).isoformat(),
            "note": "smoke-bulk",
            "tag_ids": [],
        },
    )
    if isinstance(extra, dict) and extra.get("id"):
        call("POST", "/finance/transactions/bulk-delete", {"ids": [extra["id"]]})
    call("GET", "/finance/transactions/export?format=csv")
    call("GET", "/finance/transactions/export?format=json")

    # --- биллинг: подписка (mock), способ оплаты
    call("POST", "/billing/subscription", {"plan_code": "monthly", "provider": "mock"})
    call("GET", "/billing/subscription")
    method = call(
        "POST",
        "/billing/payment-methods",
        {"kind": "card", "provider": "mock", "token": "tok_4242", "make_default": True},
    )
    if isinstance(method, dict) and method.get("id"):
        call("DELETE", f"/billing/payment-methods/{method['id']}")

    # --- профиль
    call("PATCH", "/users/me", {"timezone": "Europe/Moscow"})

    # --- уборка
    call("DELETE", f"/finance/transactions/{transaction_id}")
    if applied_id:
        call("DELETE", f"/finance/transactions/{applied_id}")
    if rule_id:
        call("DELETE", f"/finance/rules/{rule_id}")
    if template_id:
        call("DELETE", f"/finance/templates/{template_id}")
    call("DELETE", f"/finance/tags/{tag_id}")

    failed = [(name, status) for name, status in results if status >= 400]
    print()
    if failed:
        print(f"ПРОВАЛЕНО: {len(failed)} из {len(results)}")
        for name, status in failed:
            print(f"  {status}  {name}")
        return 1
    print(f"Успешно: {len(results)} запросов, все 2xx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
