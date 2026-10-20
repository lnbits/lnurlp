import asyncio
import inspect
import json
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from bolt11 import decode as bolt11_decode
from fastapi import FastAPI
from lnbits.core.models import KeyType, Payment, Wallet, WalletTypeInfo
from lnbits.db import Database
from lnbits.decorators import require_invoice_key
from lnbits.settings import settings
from lnbits.wallets.fake import FakeWallet
from pynostr.event import Event
from pynostr.key import PrivateKey
from websockets.asyncio.client import connect
from websockets.datastructures import Headers
from websockets.exceptions import InvalidStatus
from websockets.http11 import Response

from .. import crud, helpers, migrations, tasks, views_api, views_lnurl
from ..models import CreatePayLinkData, PayLinkInvoice


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def database(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "lnbits_data_folder", str(tmp_path))
    db = Database("ext_lnurlp")
    monkeypatch.setattr(crud, "db", db)
    for name, migrate in inspect.getmembers(migrations, inspect.isfunction):
        if name.startswith("m"):
            await migrate(db)
    yield db
    await db.engine.dispose()


@pytest.fixture(autouse=True)
def callback_policy(monkeypatch):
    monkeypatch.setattr(settings, "lnbits_callback_allow_private_ips", False)
    monkeypatch.setattr(settings, "lnbits_callback_url_rules", [])


@pytest.fixture
async def link(database):
    return await crud.create_pay_link(
        CreatePayLinkData(
            description="Payment",
            wallet="wallet",
            min=1,
            max=50,
            comment_chars=20,
            webhook_url="https://merchant.example/hook?token=secret",
            webhook_headers='{"Authorization":"secret"}',
            webhook_body='{"token":"secret"}',
            zaps=True,
        )
    )


@pytest.fixture
def key_info():
    return WalletTypeInfo(
        KeyType.invoice,
        Wallet(
            id="wallet", user="owner", name="Wallet", adminkey="admin", inkey="invoice"
        ),
    )


@pytest.fixture
async def client(monkeypatch, key_info):
    app = FastAPI()
    app.include_router(views_api.lnurlp_api_router, prefix="/lnurlp")
    app.include_router(views_lnurl.lnurlp_lnurl_router, prefix="/lnurlp")
    app.dependency_overrides[require_invoice_key] = lambda: key_info
    monkeypatch.setattr(
        views_api,
        "get_user",
        AsyncMock(
            return_value=SimpleNamespace(wallet_ids=["wallet", "second"], admin=False)
        ),
    )
    monkeypatch.setattr(
        views_api, "get_wallet", AsyncMock(return_value=key_info.wallet)
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://lnbits.example"
    ) as client:
        yield client


@pytest.mark.anyio
async def test_invoice_reads_filter_secrets_but_admin_can_edit(client, link, key_info):
    await crud.create_pay_link(
        CreatePayLinkData(description="Second wallet", wallet="second", min=1, max=1)
    )
    await crud.create_pay_link(
        CreatePayLinkData(description="Other owner", wallet="foreign", min=1, max=1)
    )
    for key_type in (KeyType.invoice, KeyType.admin):
        key_info.key_type = key_type
        for path in ("", "?all_wallets=true", f"/{link.id}"):
            response = await client.get(f"/lnurlp/api/v1/links{path}")
            assert response.status_code == 200
            rows = (
                response.json()
                if isinstance(response.json(), list)
                else [response.json()]
            )
            assert all(row["wallet"] != "foreign" for row in rows)
            if path == "?all_wallets=true":
                assert {row["wallet"] for row in rows} == {"wallet", "second"}
            row = next(row for row in rows if row["id"] == link.id)
            for field in ("webhook_url", "webhook_headers", "webhook_body"):
                assert row[field] == (
                    getattr(link, field) if key_type == KeyType.admin else None
                )
    public = await client.get(f"/lnurlp/api/v1/links/public/{link.id}")
    assert "secret" not in public.text


@pytest.mark.anyio
async def test_foreign_and_missing_wallet_reads_fail(client, link, monkeypatch):
    for wallet in (SimpleNamespace(user="other-owner"), None):
        monkeypatch.setattr(views_api, "get_wallet", AsyncMock(return_value=wallet))
        response = await client.get(f"/lnurlp/api/v1/links/{link.id}")
        assert response.status_code == 403


@pytest.fixture
def payment():
    return Payment(
        checking_id="checking",
        payment_hash="hash",
        wallet_id="wallet",
        amount=21000,
        fee=0,
        bolt11="invoice",
        status="success",
        extra={"tag": "lnurlp"},
    )


@pytest.mark.anyio
async def test_only_issued_invoice_is_processed_once(
    database, link, payment, monkeypatch
):
    payment.extra["link"] = link.id
    webhook = AsyncMock()
    zap = AsyncMock(return_value=None)
    monkeypatch.setattr(tasks, "send_webhook", webhook)
    monkeypatch.setattr(tasks, "send_zap", zap)
    log = Mock()
    monkeypatch.setattr(tasks, "logger", log)
    # Knowing the receiving wallet's invoice key still cannot forge provenance.
    await tasks.on_invoice_paid(payment)
    webhook.assert_not_awaited()
    log.debug.assert_called_once_with(
        "LNURLp invoice claim skipped: payment_hash={}, pay_link={}",
        payment.payment_hash,
        link.id,
    )
    await crud.create_pay_link_invoice(
        PayLinkInvoice(
            payment_hash=payment.payment_hash,
            pay_link=link.id,
            wallet_id=payment.wallet_id,
            amount=payment.amount,
        )
    )
    for change in (
        {"wallet_id": "attacker"},
        {"payment_hash": "wrong"},
        {"amount": 1000},
        {"amount": -21000},
        {"status": "pending"},
        {"status": "failed"},
    ):
        await tasks.on_invoice_paid(payment.copy(update=change))
    foreign = await crud.create_pay_link(
        CreatePayLinkData(description="Other", wallet="wallet", min=1, max=1)
    )
    forged = payment.copy(deep=True)
    forged.extra["link"] = foreign.id
    await tasks.on_invoice_paid(forged)
    webhook.assert_not_awaited()
    await asyncio.gather(
        tasks.on_invoice_paid(payment.copy(deep=True)),
        tasks.on_invoice_paid(payment.copy(deep=True)),
    )
    webhook.assert_awaited_once()
    zap.assert_awaited_once()


@pytest.mark.anyio
async def test_bad_zap_does_not_suppress_webhook(link, payment, monkeypatch):
    payment.extra.update(link=link.id, nostr="{}")
    await crud.create_pay_link_invoice(
        PayLinkInvoice(
            payment_hash=payment.payment_hash,
            pay_link=link.id,
            wallet_id=payment.wallet_id,
            amount=payment.amount,
        )
    )
    webhook = AsyncMock()
    monkeypatch.setattr(tasks, "send_webhook", webhook)
    await tasks.on_invoice_paid(payment)
    webhook.assert_awaited_once_with(payment, link, None)


@pytest.mark.anyio
async def test_listener_continues_after_failed_payment(payment, monkeypatch):
    queue = asyncio.Queue()
    queue.put_nowait(payment)
    queue.put_nowait(payment)
    monkeypatch.setattr(tasks.asyncio, "Queue", lambda: queue)
    monkeypatch.setattr(tasks, "register_invoice_listener", Mock())
    handler = AsyncMock(side_effect=[ValueError("bad event"), asyncio.CancelledError()])
    monkeypatch.setattr(tasks, "on_invoice_paid", handler)
    log = Mock()
    monkeypatch.setattr(tasks, "logger", log)
    with pytest.raises(asyncio.CancelledError):
        await tasks.wait_for_paid_invoices()
    assert handler.await_count == 2
    log.warning.assert_called_once_with(
        "LNURLp payment notification failed: {}", "ValueError"
    )


def zap_request(**changes):
    key = PrivateKey()
    event = Event(
        kind=9734,
        content="",
        tags=[
            ["p", key.public_key.hex()],
            ["amount", "21000"],
            ["relays", "wss://relay.example"],
        ],
    )
    for field, value in changes.items():
        setattr(event, field, value)
    event.sign(key.hex())
    return json.dumps(event.to_dict())


@pytest.mark.parametrize(
    "nostr",
    [
        "{}",
        "[]",
        "invalid",
        "x" * 16385,
        zap_request(kind=1),
        zap_request(tags=[["p", "00" * 32]]),
        zap_request(
            tags=[["p", "00" * 32], ["p", "11" * 32], ["relays", "wss://relay.example"]]
        ),
        zap_request(
            tags=[
                ["p", "00" * 32],
                ["amount", "1000"],
                ["relays", "wss://relay.example"],
            ]
        ),
        zap_request(tags=[["p", "bad"], ["relays", "wss://relay.example"]]),
        zap_request(tags=[["p", "00" * 32], ["relays", "file:///etc/passwd"]]),
        zap_request(
            tags=[["p", "00" * 32], ["relays", "wss://user:pass@relay.example"]]
        ),
        zap_request(
            tags=[["p", "00" * 32], ["a", "invalid"], ["relays", "wss://relay.example"]]
        ),
        zap_request(
            tags=[["p", "00" * 32], ["P", "11" * 32], ["relays", "wss://relay.example"]]
        ),
    ],
)
def test_invalid_zap_requests_are_rejected(nostr):
    with pytest.raises(ValueError, match="Invalid zap request"):
        helpers.validate_zap_request(nostr, 21000, "00" * 32)


def test_zap_signature_and_event_id_are_checked():
    nostr = zap_request()
    assert helpers.validate_zap_request(nostr, 21000, "00" * 32).kind == 9734
    for field in ("id", "sig"):
        data = json.loads(nostr)
        data[field] = "00" * (32 if field == "id" else 64)
        with pytest.raises(ValueError, match="Invalid zap request"):
            helpers.validate_zap_request(json.dumps(data), 21000, "00" * 32)


@pytest.mark.anyio
async def test_callback_records_invoice_and_signs_matching_zap(
    client, link, monkeypatch
):
    created = []
    nostr = zap_request()

    async def create_invoice(**kwargs):
        response = await FakeWallet().create_invoice(
            kwargs["amount"], unhashed_description=kwargs["unhashed_description"]
        )
        assert response.ok and response.payment_request and response.checking_id
        payment = Payment(
            checking_id=response.checking_id,
            payment_hash=bolt11_decode(response.payment_request).payment_hash,
            wallet_id=kwargs["wallet_id"],
            amount=kwargs["amount"] * 1000,
            fee=0,
            bolt11=response.payment_request,
            extra=kwargs["extra"],
        )
        created.append(payment)
        return payment

    monkeypatch.setattr(views_lnurl, "create_invoice", create_invoice)
    response = await client.get(
        f"/lnurlp/api/v1/lnurl/cb/{link.id}", params={"amount": 21000, "nostr": nostr}
    )
    assert response.status_code == 200 and "pr" in response.json()
    payment = created[0]
    queued = []

    def enqueue(coro):
        queued.append(coro)
        coro.close()

    monkeypatch.setattr(tasks.task_manager, "create_task", enqueue)
    receipt = await tasks.send_zap(payment)
    assert receipt is not None
    assert receipt.kind == 9735 and receipt.verify()
    assert ["description", nostr] in receipt.tags
    assert len(queued) == 1
    assert await crud.claim_pay_link_invoice(
        PayLinkInvoice(
            payment_hash=payment.payment_hash,
            pay_link=link.id,
            wallet_id=payment.wallet_id,
            amount=payment.amount,
        )
    )
    # A different, otherwise valid zap request cannot be attached to this invoice.
    payment.extra["nostr"] = zap_request()
    with pytest.raises(ValueError, match="does not match"):
        await tasks.send_zap(payment)
    assert len(queued) == 1


@pytest.mark.anyio
async def test_invalid_zap_does_not_create_invoice(client, link, monkeypatch):
    create = AsyncMock()
    monkeypatch.setattr(views_lnurl, "create_invoice", create)
    response = await client.get(
        f"/lnurlp/api/v1/lnurl/cb/{link.id}", params={"amount": 21000, "nostr": "{}"}
    )
    assert response.json()["status"] == "ERROR"
    create.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fe80::1", "::ffff:127.0.0.1"],
)
@pytest.mark.parametrize("scheme", ["https", "ws", "wss"])
async def test_private_and_mixed_dns_targets_are_blocked(monkeypatch, address, scheme):
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(
        loop,
        "getaddrinfo",
        AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)),
            ]
        ),
    )
    with pytest.raises(ValueError, match="not allowed"):
        await helpers.resolve_callback_addresses(f"{scheme}://callback.example")
    monkeypatch.setattr(settings, "lnbits_callback_allow_private_ips", True)
    assert await helpers.resolve_callback_addresses(f"{scheme}://callback.example") == [
        "8.8.8.8",
        address,
    ]


@pytest.mark.anyio
async def test_callback_rules_and_schemes_are_enforced(monkeypatch):
    for url in (
        "file:///etc/passwd",
        "https://user:pass@host.example",
        "wss://host.example:bad",
    ):
        with pytest.raises(ValueError):
            await helpers.resolve_callback_addresses(url)
    monkeypatch.setattr(
        settings, "lnbits_callback_url_rules", ["https://allowed.example"]
    )
    with pytest.raises(ValueError):
        await helpers.resolve_callback_addresses("wss://blocked.example")


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [200, 302])
async def test_webhook_pins_target_and_does_not_store_response(
    link, payment, monkeypatch, status_code
):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            status_code, headers={"location": "http://127.0.0.1"}, text="secret"
        )

    client_class = httpx.AsyncClient

    def client(**kwargs):
        assert kwargs == {"follow_redirects": False, "trust_env": False}
        return client_class(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(tasks.httpx, "AsyncClient", client)
    monkeypatch.setattr(
        asyncio.get_running_loop(),
        "getaddrinfo",
        AsyncMock(
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        ),
    )
    monkeypatch.setattr(tasks, "get_payment", AsyncMock(return_value=payment))
    update = AsyncMock()
    monkeypatch.setattr(tasks, "update_payment", update)
    await tasks.send_webhook(payment, link)
    assert len(seen) == 1
    assert seen[0].url.host == "8.8.8.8"
    assert seen[0].headers["host"] == "merchant.example"
    assert seen[0].headers["authorization"] == "secret"
    assert seen[0].extensions["sni_hostname"] == "merchant.example"
    assert payment.extra["wh_status"] == status_code
    assert payment.extra["wh_success"] == (status_code == 200)
    assert payment.extra["wh_response"] == ""
    assert "secret" not in str(payment.extra)
    update.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error_type,fail_second,attempts",
    [
        (httpx.ConnectError, False, 2),
        (httpx.ConnectTimeout, False, 2),
        (httpx.ConnectError, True, 2),
        (httpx.ReadTimeout, False, 1),
        (httpx.WriteError, False, 1),
    ],
)
async def test_webhook_only_retries_connection_failures(
    link, payment, monkeypatch, error_type, fail_second, attempts
):
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.host == "8.8.8.8" or fail_second:
            raise error_type("secret URL/token", request=request)
        return httpx.Response(200)

    client_class = httpx.AsyncClient
    monkeypatch.setattr(
        tasks.httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs),
    )
    monkeypatch.setattr(
        tasks,
        "resolve_callback_addresses",
        AsyncMock(return_value=["8.8.8.8", "1.1.1.1"]),
    )
    monkeypatch.setattr(tasks, "get_payment", AsyncMock(return_value=payment))
    monkeypatch.setattr(tasks, "update_payment", AsyncMock())
    log = Mock()
    monkeypatch.setattr(tasks, "logger", log)
    await tasks.send_webhook(payment, link)
    assert len(seen) == attempts
    assert all(request.headers["host"] == "merchant.example" for request in seen)
    success = attempts == 2 and not fail_second
    assert payment.extra["wh_status"] == (200 if success else -1)
    if success:
        log.warning.assert_not_called()
        assert [request.url.host for request in seen] == ["8.8.8.8", "1.1.1.1"]
    else:
        log.warning.assert_called_once_with(
            "LNURLp webhook request failed: {}", error_type.__name__
        )
    assert "secret" not in str(payment.extra)


@pytest.mark.anyio
@pytest.mark.parametrize("error_type", [OSError, asyncio.TimeoutError])
@pytest.mark.parametrize("connected", [False, True])
async def test_relay_only_retries_before_sending(monkeypatch, error_type, connected):
    error = error_type("secret URL/token")
    first_socket = SimpleNamespace(send=AsyncMock(), recv=AsyncMock(side_effect=error))
    second_socket = SimpleNamespace(send=AsyncMock(), recv=AsyncMock(return_value="OK"))
    first = Mock(
        __aenter__=AsyncMock(
            return_value=first_socket, side_effect=None if connected else error
        ),
        __aexit__=AsyncMock(return_value=False),
    )
    second = Mock(
        __aenter__=AsyncMock(return_value=second_socket),
        __aexit__=AsyncMock(return_value=False),
    )
    connect = Mock(side_effect=[first, second])
    monkeypatch.setattr(tasks.websockets, "connect", connect)
    monkeypatch.setattr(
        tasks,
        "resolve_callback_addresses",
        AsyncMock(return_value=["8.8.8.8", "1.1.1.1"]),
    )
    log = Mock()
    monkeypatch.setattr(tasks, "logger", log)
    await tasks._send_to_relay("wss://relay.example", "message")
    assert connect.call_count == (1 if connected else 2)
    if connected:
        first_socket.send.assert_awaited_once_with("message")
        second_socket.send.assert_not_awaited()
        log.warning.assert_called_once_with(
            "LNURLp relay delivery failed: {}", error_type.__name__
        )
    else:
        assert [call.kwargs["host"] for call in connect.call_args_list] == [
            "8.8.8.8",
            "1.1.1.1",
        ]
        second_socket.send.assert_awaited_once_with("message")
        log.warning.assert_not_called()


@pytest.mark.anyio
async def test_relay_pins_address_and_blocks_private_target(monkeypatch):
    loop = asyncio.get_running_loop()
    resolve = AsyncMock(
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
    )
    monkeypatch.setattr(loop, "getaddrinfo", resolve)
    connect = Mock()
    monkeypatch.setattr(tasks.websockets, "connect", connect)
    await tasks._send_to_relay("wss://relay.example", "message")
    connect.assert_not_called()
    resolve.return_value = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))
    ]
    websocket = SimpleNamespace(send=AsyncMock(), recv=AsyncMock(return_value='["OK"]'))
    connection = Mock(
        __aenter__=AsyncMock(return_value=websocket), __aexit__=AsyncMock()
    )
    connect.return_value = connection
    await tasks._send_to_relay("wss://relay.example", "message")
    assert connect.call_args.kwargs["host"] == "8.8.8.8"
    assert connect.call_args.kwargs["port"] == 443
    assert connect.call_args.kwargs["proxy"] is None
    websocket.send.assert_awaited_once_with("message")


@pytest.mark.anyio
async def test_relay_redirect_cannot_change_destination():
    connection = connect("wss://relay.example", host="8.8.8.8", port=443, proxy=None)
    error = connection.process_redirect(
        InvalidStatus(Response(302, "Found", Headers({"Location": "wss://127.0.0.1"})))
    )
    assert isinstance(error, ValueError)


@pytest.mark.anyio
async def test_public_activity_does_not_overwrite_owner_settings(link):
    stale = await crud.get_pay_link(link.id)
    assert stale is not None
    link.webhook_url = "https://new.example"
    await crud.update_pay_link(link)
    await asyncio.gather(
        crud.mark_pay_link_served_meta(stale.id), crud.mark_pay_link_served_pr(stale.id)
    )
    saved = await crud.get_pay_link(link.id)
    assert saved is not None
    assert saved.webhook_url == "https://new.example"
    assert saved.served_meta == saved.served_pr == 1
