import asyncio
import json
import time
from threading import Thread
from typing import List

import httpx
from lnbits.core.crud import update_payment_extra
from lnbits.core.models import Payment
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener
from loguru import logger
from websocket import WebSocketApp

from .crud import get_or_create_lnurlp_settings, get_pay_link
from .models import PayLink
from .nostr.event import EncryptedDirectMessage


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, get_current_extension_name())

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment):
    if not payment.extra:
        return

    if payment.extra.get("tag") != "lnurlp":
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

    await send_webhook(payment, pay_link)

    if pay_link.zaps:
        await send_zap(payment)


async def send_webhook(payment: Payment, pay_link: PayLink):
    if not pay_link.webhook_url:
        return

    async with httpx.AsyncClient() as client:
        try:
            r: httpx.Response = await client.post(
                pay_link.webhook_url,
                json={
                    "payment_hash": payment.payment_hash,
                    "payment_request": payment.bolt11,
                    "amount": payment.amount,
                    "comment": payment.extra.get("comment"),
                    "webhook_data": payment.extra.get("webhook_data") or "",
                    "lnurlp": pay_link.id,
                    "body": (
                        json.loads(pay_link.webhook_body)
                        if pay_link.webhook_body
                        else ""
                    ),
                },
                headers=(
                    json.loads(pay_link.webhook_headers)
                    if pay_link.webhook_headers
                    else None
                ),
                timeout=40,
            )
            await mark_webhook_sent(
                payment.payment_hash,
                r.status_code,
                r.is_success,
                r.reason_phrase,
                r.text,
            )
        except Exception as exc:
            logger.error(exc)
            await mark_webhook_sent(
                payment.payment_hash, -1, False, "Unexpected Error", str(exc)
            )


async def mark_webhook_sent(
    payment_hash: str, status: int, is_success: bool, reason_phrase="", text=""
) -> None:
    await update_payment_extra(
        payment_hash,
        {
            "wh_status": status,  # keep for backwards compability
            "wh_success": is_success,
            "wh_message": reason_phrase,
            "wh_response": text,
        },
    )


# NIP-57 - load the zap request
async def send_zap(payment: Payment):
    nostr = payment.extra.get("nostr") if payment.extra else None
    if not nostr:
        return

    event_json = json.loads(nostr)

    def get_tag(event_json, tag):
        res = [event_tag[1:] for event_tag in event_json["tags"] if event_tag[0] == tag]
        return res[0] if res else None

    tags = []
    for t in ["p", "e"]:
        tag = get_tag(event_json, t)
        if tag:
            tags.append([t, tag[0]])
    tags.append(["bolt11", payment.bolt11])
    tags.append(["description", nostr])

    pubkey = next((pk[1] for pk in tags if pk[0] == "p"), None)
    assert pubkey, "Cannot create zap receipt. Recepient pubkey is missing."
    zap_receipt = EncryptedDirectMessage(
        kind=9735,
        recipient_pubkey=pubkey,
        tags=tags,
        content=payment.extra.get("comment") or "",
        cleartext_content=payment.extra.get("comment") or "",
    )

    settings = await get_or_create_lnurlp_settings()
    settings.private_key.sign_event(zap_receipt)

    def send(relay):
        def send_event(_):
            logger.debug(f"Sending zap to {ws.url}")
            ws.send(zap_receipt.to_message())
            time.sleep(2)
            ws.close()

        ws = WebSocketApp(relay, on_open=send_event)
        wst = Thread(target=ws.run_forever, name=f"LNURL zap {relay}")
        wst.daemon = True
        wst.start()
        return ws, wst

    # list of all websockets
    wss: List[WebSocketApp] = []
    # list of all threads for these websockets
    wsts: List[Thread] = []

    # # send zap via nostrclient
    # ws, wst = send(f"wss://localhost:{settings.port}/nostrclient/api/v1/relay")
    # wss += [ws]
    # wsts += [wst]

    # send zap receipt to relays in zap request
    relays = get_tag(event_json, "relays")
    if relays:
        if len(relays) > 50:
            relays = relays[:50]
        for r in relays:
            ws, wst = send(r)
            wss += [ws]
            wsts += [wst]

    await asyncio.sleep(10)
    for ws, wst in zip(wss, wsts):
        logger.debug(f"Closing websocket {ws.url}")
        ws.close()
        wst.join()
