from datetime import datetime, timezone

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash
from pynostr.key import PrivateKey

from .models import CreatePayLinkData, LnurlpSettings, PayLink, PayLinkInvoice

db = Database("ext_lnurlp")


async def get_or_create_lnurlp_settings() -> LnurlpSettings:
    settings = await db.fetchone(
        "SELECT * FROM lnurlp.settings LIMIT 1", model=LnurlpSettings
    )
    if settings:
        return settings
    else:
        settings = LnurlpSettings(nostr_private_key=PrivateKey().hex())
        await db.insert("lnurlp.settings", settings)
        return settings


async def update_lnurlp_settings(settings: LnurlpSettings) -> LnurlpSettings:
    await db.update("lnurlp.settings", settings, "")
    return settings


async def delete_lnurlp_settings() -> None:
    await db.execute("DELETE FROM lnurlp.settings")


async def get_pay_link_by_username(username: str) -> PayLink | None:
    return await db.fetchone(
        "SELECT * FROM lnurlp.pay_links WHERE username = :username",
        {"username": username},
        PayLink,
    )


async def create_pay_link(data: CreatePayLinkData) -> PayLink:
    link_id = urlsafe_short_hash()[:6]

    assert data.wallet, "Wallet is required"
    now = datetime.now(timezone.utc)

    link = PayLink(
        id=link_id,
        wallet=data.wallet,
        description=data.description,
        min=data.min,
        max=data.max,
        served_meta=0,
        served_pr=0,
        username=data.username,
        zaps=data.zaps,
        webhook_url=data.webhook_url,
        webhook_headers=data.webhook_headers,
        webhook_body=data.webhook_body,
        success_text=data.success_text,
        success_url=data.success_url,
        currency=data.currency,
        comment_chars=data.comment_chars,
        fiat_base_multiplier=data.fiat_base_multiplier,
        created_at=now,
        updated_at=now,
        disposable=data.disposable if data.disposable is not None else True,
        domain=data.domain,
    )

    await db.insert("lnurlp.pay_links", link)
    return link


async def get_address_data(username: str) -> PayLink | None:
    return await db.fetchone(
        "SELECT * FROM lnurlp.pay_links WHERE username = :username",
        {"username": username},
        PayLink,
    )


async def get_pay_link(link_id: str) -> PayLink | None:
    return await db.fetchone(
        "SELECT * FROM lnurlp.pay_links WHERE id = :id",
        {"id": link_id},
        PayLink,
    )


async def get_pay_links(wallet_ids: str | list[str]) -> list[PayLink]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM lnurlp.pay_links WHERE wallet IN ({q}) ORDER BY Id",
        model=PayLink,
    )


async def update_pay_link(link: PayLink) -> PayLink:
    link.updated_at = datetime.now(timezone.utc)
    await db.update("lnurlp.pay_links", link)
    return link


async def delete_pay_link(link_id: str) -> None:
    await db.execute("DELETE FROM lnurlp.pay_links WHERE id = :id", {"id": link_id})


async def mark_pay_link_served_meta(link_id: str) -> None:
    await db.execute(
        "UPDATE lnurlp.pay_links SET served_meta = 1 WHERE id = :id",
        {"id": link_id},
    )


async def mark_pay_link_served_pr(link_id: str) -> None:
    await db.execute(
        "UPDATE lnurlp.pay_links SET served_pr = 1 WHERE id = :id",
        {"id": link_id},
    )


async def create_pay_link_invoice(invoice: PayLinkInvoice) -> None:
    await db.insert("lnurlp.invoices", invoice)


async def claim_pay_link_invoice(invoice: PayLinkInvoice) -> bool:
    result = await db.execute(
        """
        UPDATE lnurlp.invoices SET processed = true
        WHERE payment_hash = :payment_hash AND pay_link = :pay_link
            AND wallet_id = :wallet_id AND amount = :amount AND processed = false
        """,
        {
            "payment_hash": invoice.payment_hash,
            "pay_link": invoice.pay_link,
            "wallet_id": invoice.wallet_id,
            "amount": invoice.amount,
        },
    )
    return result.rowcount == 1
