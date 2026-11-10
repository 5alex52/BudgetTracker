"""Import of records from exported files (CSV and JSON of the export endpoint)."""

import json

import pytest
from fastapi import HTTPException
from src.finance.dao import AccountDAO
from src.finance.dao import CategoryDAO
from src.finance.schemas import AccountCreate
from src.finance.schemas import AccountType
from src.finance.schemas import TransactionImportRequest
from src.finance.service import AccountService
from src.finance.service import TransactionService

CSV_HEADER = "date,type,account,category,amount,currency,note"


@pytest.mark.asyncio
async def test_csv_import_creates_missing_account_and_category(user, currencies, session_maker):
    content = "\n".join(
        [
            CSV_HEADER,
            "2026-01-05 10:00,expense,Coffee Shop,Products,3.50,USD,latte",
            "2026-01-06,income,Coffee Shop,Salary,100.00,USD,pay",
        ]
    )

    result = await TransactionService.import_from_text(
        payload=TransactionImportRequest(format="csv", content=content),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert result.created == 2
    assert result.skipped == 0
    assert result.accounts_created == 1
    assert result.categories_created == 2

    async with session_maker() as session:
        accounts = await AccountDAO.find_all_by_user(session, user.id, limit=500)
        categories = await CategoryDAO.find_all_by_user(session, user.id, limit=1000)

    coffee = [account for account in accounts if account.name == "Coffee Shop"]
    assert len(coffee) == 1
    assert float(coffee[0].balance) == pytest.approx(96.5)
    assert {("Products", "expense"), ("Salary", "income")}.issubset(
        {(category.name, category.type.value) for category in categories}
    )


@pytest.mark.asyncio
async def test_json_import_reuses_existing_account(user, currencies, session_maker):
    await AccountService.create_for_user(
        schema=AccountCreate(name="Main", type=AccountType.CHECKING, currency_id="USD", balance=50.0),
        user_id=user.id,
        session_maker=session_maker,
    )
    content = json.dumps(
        [
            {
                "date": "2026-02-01T12:00:00",
                "type": "expense",
                "account_name": "Main",
                "category_name": "Transport",
                "amount": 5.0,
                "currency_id": "USD",
                "note": None,
            },
            {
                "date": "2026-02-02T12:00:00",
                "type": "expense",
                "account_name": "Main",
                "category_name": "Transport",
                "amount": 4.0,
                "currency_id": "USD",
                "note": "taxi",
            },
        ]
    )

    result = await TransactionService.import_from_text(
        payload=TransactionImportRequest(format="json", content=content),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert result.created == 2
    assert result.accounts_created == 0
    assert result.categories_created == 1


@pytest.mark.asyncio
async def test_import_skips_transfers_and_bad_rows(user, currencies, session_maker):
    content = "\n".join(
        [
            CSV_HEADER,
            "2026-01-05 10:00,transfer,Main,Other,10.00,USD,move",
            "2026-01-05 10:00,expense,Main,Products,-3.00,USD,negative",
            "not-a-date,expense,Main,Products,3.00,USD,bad date",
        ]
    )

    result = await TransactionService.import_from_text(
        payload=TransactionImportRequest(format="csv", content=content),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert result.created == 0
    assert result.skipped == 3
    assert any("transfer" in error for error in result.errors)


@pytest.mark.asyncio
async def test_import_rejects_unknown_csv_header(user, session_maker):
    with pytest.raises(HTTPException) as error:
        await TransactionService.import_from_text(
            payload=TransactionImportRequest(format="csv", content="a,b,c\n1,2,3"),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400
