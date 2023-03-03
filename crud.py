import re
from typing import List, Optional, Union

from lnbits.helpers import urlsafe_short_hash

from . import db #, maindb
from .models import CreatePayLinkData, PayLink

from loguru import logger

async def create_pay_link(data: CreatePayLinkData, wallet_id: str) -> PayLink:
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
            username

        )
        VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ),
    )
    assert result

    link = await get_pay_link(link_id)
    assert link, "Newly created link couldn't be retrieved"
    return link



async def check_lnaddress_update(username: str, id: str) -> bool:
    # check no duplicates for lnaddress when updating an username
    row = await db.fetchall(
        "SELECT username FROM lnurlp.pay_links WHERE username = ? AND id = ?",
        (username, id),
    )
    logger.info("number of rows from username search")
    logger.info(len(row))
    if len(row) > 1:
        assert False, "Lightning Address Already exists. Try a different One?"
        return
    else:
        return True


async def check_lnaddress_exists(username: str) -> bool:
    # check if lnaddress username exists in the database when creating a new entry
    row = await db.fetchall(
        "SELECT username FROM lnurlp.pay_links WHERE username = ?", (username,)
    )
    logger.info("number of rows from lnaddress search")
    if row:
        assert False, "Lighting Address Already exists. Try a different One?"
        return
    else:
        return True


async def check_lnaddress_format(username: str) -> bool:
    # check username complies with lnaddress specification
    if not re.match("^[a-z0-9-_.]{3,15}$", username):
        assert False, "Only letters a-z0-9-_. allowed, min 3 and max 15 characters!"
        return
    return True

# async def get_wallet_key(wallet_id: str) -> str:
#     row = await maindb.fetchone("SELECT inkey FROM wallets WHERE id = ?", (wallet_id,))
#     if row is not None:
#         return row[0]
#     else:
#         assert False, "Cannot locate wallet invoice key"
#         return
    
async def get_address_data(username: str) -> Optional[PayLink]:
    row = await db.fetchone(
        "SELECT * FROM lnurl.pay_links WHERE username = ?", (username,)
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


async def update_pay_link(link_id: int, **kwargs) -> Optional[PayLink]:
    q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE lnurlp.pay_links SET {q} WHERE id = ?", (*kwargs.values(), link_id)
    )
    row = await db.fetchone("SELECT * FROM lnurlp.pay_links WHERE id = ?", (link_id,))
    return PayLink.from_row(row) if row else None


async def increment_pay_link(link_id: int, **kwargs) -> Optional[PayLink]:
    q = ", ".join([f"{field[0]} = {field[0]} + ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE lnurlp.pay_links SET {q} WHERE id = ?", (*kwargs.values(), link_id)
    )
    row = await db.fetchone("SELECT * FROM lnurlp.pay_links WHERE id = ?", (link_id,))
    return PayLink.from_row(row) if row else None


async def delete_pay_link(link_id: int) -> None:
    await db.execute("DELETE FROM lnurlp.pay_links WHERE id = ?", (link_id,))
