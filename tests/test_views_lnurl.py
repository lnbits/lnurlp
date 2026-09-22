from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError  # type: ignore[import-untyped]

from ..models import PayLink
from ..views_lnurl import (
    configured_lnaddress_domain,
    create_default_lnaddress,
    lnaddress,
)


def pay_link(link_id: str = "link-id") -> PayLink:
    return PayLink(
        id=link_id,
        wallet="wallet-id",
        description="Payment to alice",
        min=1,
        max=100,
        served_meta=0,
        served_pr=0,
        comment_chars=0,
        disposable=False,
        username="alice",
        zaps=True,
        domain="lnbits.example.com",
    )


def test_configured_lnaddress_domain(monkeypatch):
    monkeypatch.setattr(
        "lnurlp.views_lnurl.settings.lnbits_baseurl",
        "https://LNbits.example.com:443/some/path",
    )

    assert configured_lnaddress_domain() == "lnbits.example.com"


def test_configured_lnaddress_domain_rejects_invalid_baseurl(monkeypatch):
    monkeypatch.setattr(
        "lnurlp.views_lnurl.settings.lnbits_baseurl", "lnbits.example.com"
    )

    assert configured_lnaddress_domain() is None


@pytest.mark.asyncio
async def test_lnaddress_preserves_existing_manual_link(monkeypatch):
    link = pay_link()

    async def response(_: object, link_id: str):
        return {"link_id": link_id}

    async def get_existing(_: str):
        return link

    monkeypatch.setattr("lnurlp.views_lnurl.get_address_data", get_existing)
    monkeypatch.setattr("lnurlp.views_lnurl.api_lnurl_response", response)

    response = await lnaddress("alice", object())

    assert response == {"link_id": link.id}


@pytest.mark.asyncio
async def test_create_default_lnaddress_returns_none_for_unknown_account(monkeypatch):
    async def no_account(_: str):
        return None

    monkeypatch.setattr("lnurlp.views_lnurl.get_account_by_username", no_account)

    assert await create_default_lnaddress("alice") is None


@pytest.mark.asyncio
async def test_create_default_lnaddress_uses_account_and_server_defaults(monkeypatch):
    captured = {}
    account = SimpleNamespace(username="Alice")
    user = SimpleNamespace(
        wallets=[
            SimpleNamespace(id="send-only", can_receive_payments=False),
            SimpleNamespace(id="receive", can_receive_payments=True),
        ]
    )
    created_link = pay_link("created-link")

    async def get_existing(_: str):
        return None

    async def create(data):
        captured["data"] = data
        return created_link

    async def get_account(_: str):
        return account

    async def get_user(_: object):
        return user

    monkeypatch.setattr("lnurlp.views_lnurl.get_address_data", get_existing)
    monkeypatch.setattr("lnurlp.views_lnurl.get_account_by_username", get_account)
    monkeypatch.setattr("lnurlp.views_lnurl.get_user_from_account", get_user)
    monkeypatch.setattr("lnurlp.views_lnurl.create_pay_link", create)
    monkeypatch.setattr(
        "lnurlp.views_lnurl.settings.lnbits_baseurl", "https://LNbits.example.com"
    )
    monkeypatch.setattr(
        "lnurlp.views_lnurl.settings.lnbits_max_incoming_payment_amount_sats", 500_000
    )

    assert await create_default_lnaddress("ALICE") == created_link
    data = captured["data"]
    assert data.username == "alice"
    assert data.wallet == "receive"
    assert data.domain == "lnbits.example.com"
    assert data.min == 1
    assert data.max == 500_000
    assert data.zaps is True
    assert data.disposable is False


@pytest.mark.asyncio
async def test_create_default_lnaddress_uses_database_maximum_without_server_cap(
    monkeypatch,
):
    account = SimpleNamespace(username="alice")
    user = SimpleNamespace(
        wallets=[SimpleNamespace(id="receive", can_receive_payments=True)]
    )
    captured = {}

    async def get_existing(_: str):
        return None

    async def create(data):
        captured["maximum"] = data.max
        return pay_link()

    async def get_account(_: str):
        return account

    async def get_user(_: object):
        return user

    monkeypatch.setattr("lnurlp.views_lnurl.get_address_data", get_existing)
    monkeypatch.setattr("lnurlp.views_lnurl.get_account_by_username", get_account)
    monkeypatch.setattr("lnurlp.views_lnurl.get_user_from_account", get_user)
    monkeypatch.setattr("lnurlp.views_lnurl.create_pay_link", create)
    monkeypatch.setattr(
        "lnurlp.views_lnurl.settings.lnbits_baseurl", "https://lnbits.example.com"
    )
    monkeypatch.setattr(
        "lnurlp.views_lnurl.settings.lnbits_max_incoming_payment_amount_sats", 0
    )

    await create_default_lnaddress("alice")

    assert captured["maximum"] == 2_147_483_647


@pytest.mark.asyncio
async def test_create_default_lnaddress_caps_maximum_at_database_limit(monkeypatch):
    account = SimpleNamespace(username="alice")
    user = SimpleNamespace(
        wallets=[SimpleNamespace(id="receive", can_receive_payments=True)]
    )
    captured = {}

    async def get_existing(_: str):
        return None

    async def create(data):
        captured["maximum"] = data.max
        return pay_link()

    async def get_account(_: str):
        return account

    async def get_user(_: object):
        return user

    monkeypatch.setattr("lnurlp.views_lnurl.get_address_data", get_existing)
    monkeypatch.setattr("lnurlp.views_lnurl.get_account_by_username", get_account)
    monkeypatch.setattr("lnurlp.views_lnurl.get_user_from_account", get_user)
    monkeypatch.setattr("lnurlp.views_lnurl.create_pay_link", create)
    monkeypatch.setattr(
        "lnurlp.views_lnurl.settings.lnbits_baseurl", "https://lnbits.example.com"
    )
    monkeypatch.setattr(
        "lnurlp.views_lnurl.settings.lnbits_max_incoming_payment_amount_sats",
        3_000_000_000,
    )

    await create_default_lnaddress("alice")

    assert captured["maximum"] == 2_147_483_647


@pytest.mark.asyncio
async def test_create_default_lnaddress_returns_race_winner(monkeypatch):
    account = SimpleNamespace(username="alice")
    user = SimpleNamespace(
        wallets=[SimpleNamespace(id="receive", can_receive_payments=True)]
    )
    winner = pay_link("winner")
    calls = 0

    async def get_existing(_: str):
        nonlocal calls
        calls += 1
        return winner if calls == 2 else None

    async def create(_: object):
        raise IntegrityError("INSERT", {}, Exception("duplicate username"))

    async def get_account(_: str):
        return account

    async def get_user(_: object):
        return user

    monkeypatch.setattr("lnurlp.views_lnurl.get_address_data", get_existing)
    monkeypatch.setattr("lnurlp.views_lnurl.get_account_by_username", get_account)
    monkeypatch.setattr("lnurlp.views_lnurl.get_user_from_account", get_user)
    monkeypatch.setattr("lnurlp.views_lnurl.create_pay_link", create)
    monkeypatch.setattr(
        "lnurlp.views_lnurl.settings.lnbits_baseurl", "https://lnbits.example.com"
    )

    assert await create_default_lnaddress("alice") == winner
