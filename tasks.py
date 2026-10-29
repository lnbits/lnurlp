import asyncio
import hashlib
import json
from urllib.parse import urlsplit

import httpx
import websockets
from bolt11 import decode as bolt11_decode
from lnbits.core.crud import get_payment, update_payment
from lnbits.core.models import Payment
from lnbits.task_manager import task_manager
from lnbits.tasks import register_invoice_listener
from loguru import logger
from pynostr.event import Event

from .crud import claim_pay_link_invoice, get_or_create_lnurlp_settings, get_pay_link
from .helpers import resolve_callback_addresses, validate_zap_request
from .models import PayLink, PayLinkInvoice


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_lnurlp")

    while True:
        payment = await invoice_queue.get()
        try:
            await on_invoice_paid(payment)
        except Exception as exc:
            logger.warning("LNURLp payment notification failed: {}", type(exc).__name__)


async def on_invoice_paid(payment: Payment):
    if (
        not payment.extra
        or payment.extra.get("tag") != "lnurlp"
        or not payment.success
        or not payment.is_in
    ):
        return

    if payment.extra.get("wh_status"):
        # this webhook has already been sent
        return

    pay_link_id = payment.extra.get("link")
    if not pay_link_id:
        logger.error("Invoice paid. But no pay link id found.")
        return

    pay_link = await get_pay_link(pay_link_id)
    if not pay_link:
        logger.error(f"Invoice paid. But Pay link `{pay_link_id}` not found.")
        return

    # shortcut: no retries after a crash; add durable delivery when required.
    if not await claim_pay_link_invoice(
        PayLinkInvoice(
            payment_hash=payment.payment_hash,
            pay_link=pay_link.id,
            wallet_id=payment.wallet_id,
            amount=payment.amount,
        )
    ):
        logger.debug(
            "LNURLp invoice claim skipped: payment_hash={}, pay_link={}",
            payment.payment_hash,
            pay_link.id,
        )
        return

    zap_receipt = None
    if pay_link.zaps:
        try:
            zap_receipt = await send_zap(payment)
        except Exception as exc:
            logger.warning("LNURLp zap receipt failed: {}", type(exc).__name__)

    await send_webhook(
        payment, pay_link, zap_receipt.to_message() if zap_receipt else None
    )


async def send_webhook(payment: Payment, pay_link: PayLink, zap_receipt=None):
    if not pay_link.webhook_url:
        return

    try:
        url = httpx.URL(pay_link.webhook_url)
        addresses = await resolve_callback_addresses(str(url))
        headers = (
            json.loads(pay_link.webhook_headers) if pay_link.webhook_headers else {}
        )
        headers = httpx.Headers(headers)
        headers["Host"] = urlsplit(str(url)).netloc
        async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as client:
            for address in addresses:
                try:
                    async with client.stream(
                        "POST",
                        url.copy_with(host=address),
                        json={
                            "payment_hash": payment.payment_hash,
                            "payment_request": payment.bolt11,
                            "amount": payment.amount,
                            "comment": (
                                payment.extra.get("comment") if payment.extra else None
                            ),
                            "webhook_data": (
                                payment.extra.get("webhook_data")
                                if payment.extra
                                else None
                            ),
                            "lnurlp": pay_link.id,
                            "body": (
                                json.loads(pay_link.webhook_body)
                                if pay_link.webhook_body
                                else ""
                            ),
                            "zap_receipt": zap_receipt or "",
                        },
                        headers=headers,
                        extensions={"sni_hostname": url.host},
                        timeout=6,
                    ) as response:
                        await mark_webhook_sent(
                            payment.checking_id,
                            response.status_code,
                            response.is_success,
                            (
                                "Webhook delivered."
                                if response.is_success
                                else "Webhook failed."
                            ),
                        )
                    return
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    if address == addresses[-1]:
                        raise
    except Exception as exc:
        logger.warning("LNURLp webhook request failed: {}", type(exc).__name__)
        await mark_webhook_sent(
            payment.checking_id, -1, False, "Webhook request failed."
        )


async def mark_webhook_sent(
    checking_id: str, status: int, is_success: bool, reason_phrase=""
) -> None:
    payment = await get_payment(checking_id)
    extra = payment.extra or {}
    extra["wh_status"] = status  # keep for backwards compability
    extra["wh_success"] = is_success
    extra["wh_message"] = reason_phrase
    # Webhook responses can echo credentials into invoice-key-readable metadata.
    extra["wh_response"] = ""
    payment.extra = extra
    await update_payment(payment)


# NIP-57 - load the zap request
async def send_zap(payment: Payment):
    nostr = payment.extra.get("nostr") if payment.extra else None
    if not nostr:
        return

    settings = await get_or_create_lnurlp_settings()
    event = validate_zap_request(nostr, payment.amount, settings.public_key)
    assert event.pubkey
    invoice = bolt11_decode(payment.bolt11)
    if (
        invoice.payment_hash != payment.payment_hash
        or invoice.amount_msat != payment.amount
        or invoice.description_hash != hashlib.sha256(nostr.encode()).hexdigest()
    ):
        raise ValueError("Zap request does not match the paid invoice.")

    tags = [[tag[0], tag[1]] for tag in event.tags if tag[0] in {"p", "e", "a"}]
    tags.append(["P", event.pubkey])
    tags.append(["bolt11", payment.bolt11])
    tags.append(["description", nostr])

    zap_receipt = Event(
        kind=9735,
        tags=tags,
        content="",
        created_at=int(payment.updated_at.timestamp()),
    )

    zap_receipt.sign(settings.private_key.hex())
    relays = next(tag[1:] for tag in event.tags if tag[0] == "relays")[:50]
    for relay in relays:
        task_manager.create_task(_send_to_relay(relay, zap_receipt.to_message()))

    return zap_receipt


async def _send_to_relay(relay_url: str, event_message: str) -> None:
    try:
        addresses = await resolve_callback_addresses(relay_url)
        parsed = urlsplit(relay_url)
        for address in addresses:
            connected = False
            try:
                async with websockets.connect(
                    relay_url,
                    host=address,
                    port=parsed.port or (443 if parsed.scheme == "wss" else 80),
                    proxy=None,
                    open_timeout=5,
                    close_timeout=1,
                    max_size=16384,
                ) as websocket:
                    connected = True
                    await websocket.send(event_message)
                    await asyncio.wait_for(websocket.recv(), timeout=5)
                return
            except (OSError, asyncio.TimeoutError):
                if connected or address == addresses[-1]:
                    raise
    except Exception as exc:
        logger.warning("LNURLp relay delivery failed: {}", type(exc).__name__)
