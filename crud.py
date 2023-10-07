from typing import List, Optional, Union

from lnbits.helpers import urlsafe_short_hash

from . import db
from .models import CreatePayLinkData, LnurlpSettings, PayLink
from .services import check_lnaddress_format
from .nostr.key import PrivateKey


async def get_or_create_lnurlp_settings() -> LnurlpSettings:
    row = await db.fetchone("SELECT * FROM lnurlp.settings LIMIT 1")
    if row:
        return LnurlpSettings(**row)
    else:

        private_key = PrivateKey()
        nostr_public_key = private_key.public_key.hex()
        nostr_private_key = private_key.hex()
        await db.execute(
            """
            INSERT INTO lnurlp.settings (nostr_private_key) VALUES (?)
            """
            , (nostr_private_key, nostr_public_key)
        )
        return LnurlpSettings(nostr_private_key=nostr_private_key)


async def update_lnurlp_settings(settings: LnurlpSettings) -> LnurlpSettings:
    await db.execute(
        """
        UPDATE lnurlp.settings SET (nostr_private_key) VALUES (?)
        """
        , (settings.nostr_private_key,)
    )
    return settings


async def delete_lnurlp_settings() -> None:
    await db.fetchone("DELETE FROM lnurlp.settings")


async def check_lnaddress_not_exists(username: str) -> bool:
    # check if lnaddress username exists in the database when creating a new entry
    row = await db.fetchall(
        "SELECT username FROM lnurlp.pay_links WHERE username = ?", (username,)
    )
    if row:
        raise Exception("Username already exists. Try a different one.")
    else:
        return True


async def create_pay_link(data: CreatePayLinkData, wallet_id: str) -> PayLink:
    if data.username:
        await check_lnaddress_format(data.username)
        await check_lnaddress_not_exists(data.username)

    link_id = urlsafe_short_hash()[:6]

    result = await db.execute(
        """
        INSERT INTO lnurlp.pay_links (
            id,
            wallet,
            description,
            min,
            max,
            served_meta,
            served_pr,
            webhook_url,
            webhook_headers,
            webhook_body,
            success_text,
            success_url,
            comment_chars,
            currency,
            fiat_base_multiplier,
            username,
            zaps

        )
        VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            link_id,
            wallet_id,
            data.description,
            data.min,
            data.max,
            data.webhook_url,
            data.webhook_headers,
            data.webhook_body,
            data.success_text,
            data.success_url,
            data.comment_chars,
            data.currency,
            data.fiat_base_multiplier,
            data.username,
            data.zaps,
        ),
    )
    assert result

    link = await get_pay_link(link_id)
    assert link, "Newly created link couldn't be retrieved"
    return link


async def get_address_data(username: str) -> Optional[PayLink]:
    row = await db.fetchone(
        "SELECT * FROM lnurlp.pay_links WHERE username = ?", (username,)
    )
    return PayLink.from_row(row) if row else None


async def get_pay_link(link_id: str) -> Optional[PayLink]:
    row = await db.fetchone("SELECT * FROM lnurlp.pay_links WHERE id = ?", (link_id,))
    return PayLink.from_row(row) if row else None


async def get_pay_links(wallet_ids: Union[str, List[str]]) -> List[PayLink]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join(["?"] * len(wallet_ids))
    rows = await db.fetchall(
        f"""
        SELECT * FROM lnurlp.pay_links WHERE wallet IN ({q})
        ORDER BY Id
        """,
        (*wallet_ids,),
    )
    return [PayLink.from_row(row) for row in rows]


async def update_pay_link(link_id: str, **kwargs) -> Optional[PayLink]:
    if "username" in kwargs and len(kwargs["username"] or "") > 0:
        await check_lnaddress_format(kwargs["username"])
        await check_lnaddress_not_exists(kwargs["username"])

    q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE lnurlp.pay_links SET {q} WHERE id = ?", (*kwargs.values(), link_id)
    )
    row = await db.fetchone("SELECT * FROM lnurlp.pay_links WHERE id = ?", (link_id,))
    return PayLink.from_row(row) if row else None


async def increment_pay_link(link_id: str, **kwargs) -> Optional[PayLink]:
    q = ", ".join([f"{field[0]} = {field[0]} + ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE lnurlp.pay_links SET {q} WHERE id = ?", (*kwargs.values(), link_id)
    )
    row = await db.fetchone("SELECT * FROM lnurlp.pay_links WHERE id = ?", (link_id,))
    return PayLink.from_row(row) if row else None


async def delete_pay_link(link_id: str) -> None:
    await db.execute("DELETE FROM lnurlp.pay_links WHERE id = ?", (link_id,))
