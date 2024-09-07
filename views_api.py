import json
import re
from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from lnbits.core.crud import get_user, get_wallet
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import (
    check_admin,
    require_admin_key,
    require_invoice_key,
)
from lnbits.utils.exchange_rates import currencies, get_fiat_rate_satoshis
from lnurl.exceptions import InvalidUrl as LnurlInvalidUrl
from starlette.exceptions import HTTPException

from .crud import (
    create_pay_link,
    delete_lnurlp_settings,
    delete_pay_link,
    get_or_create_lnurlp_settings,
    get_pay_link,
    get_pay_link_by_username,
    get_pay_links,
    update_lnurlp_settings,
    update_pay_link,
)
from .helpers import parse_nostr_private_key
from .models import CreatePayLinkData, LnurlpSettings

lnurlp_api_router = APIRouter()


@lnurlp_api_router.get("/api/v1/currencies")
async def api_list_currencies_available():
    return list(currencies.keys())


@lnurlp_api_router.get("/api/v1/links", status_code=HTTPStatus.OK)
async def api_links(
    req: Request,
    key_info: WalletTypeInfo = Depends(require_invoice_key),
    all_wallets: bool = Query(False),
):
    wallet_ids = [key_info.wallet.id]

    if all_wallets:
        user = await get_user(key_info.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    try:
        return [
            {**link.dict(), "lnurl": link.lnurl(req)}
            for link in await get_pay_links(wallet_ids)
        ]

    except LnurlInvalidUrl as exc:
        raise HTTPException(
            status_code=HTTPStatus.UPGRADE_REQUIRED,
            detail=(
                "LNURLs need to be delivered over a publicly "
                "accessible `https` domain or Tor onion."
            ),
        ) from exc


@lnurlp_api_router.get("/api/v1/links/{link_id}", status_code=HTTPStatus.OK)
async def api_link_retrieve(
    r: Request, link_id: str, key_info: WalletTypeInfo = Depends(require_invoice_key)
):
    link = await get_pay_link(link_id)

    if not link:
        raise HTTPException(
            detail="Pay link does not exist.", status_code=HTTPStatus.NOT_FOUND
        )

    link_wallet = await get_wallet(link.wallet)

    # admins are allowed to read paylinks beloging to regular users
    user = await get_user(key_info.wallet.user)
    admin_user = user.admin if user else False
    if not admin_user and link_wallet and link_wallet.user != key_info.wallet.user:
        raise HTTPException(
            detail="Not your pay link.", status_code=HTTPStatus.FORBIDDEN
        )

    return {**link.dict(), **{"lnurl": link.lnurl(r)}}


async def check_username_exists(username: str):
    prev_link = await get_pay_link_by_username(username)
    if prev_link:
        raise HTTPException(
            detail="Username already taken.",
            status_code=HTTPStatus.CONFLICT,
        )


@lnurlp_api_router.post("/api/v1/links", status_code=HTTPStatus.CREATED)
@lnurlp_api_router.put("/api/v1/links/{link_id}", status_code=HTTPStatus.OK)
async def api_link_create_or_update(
    data: CreatePayLinkData,
    request: Request,
    link_id: Optional[str] = None,
    key_info: WalletTypeInfo = Depends(require_admin_key),
):
    if data.min > data.max:
        raise HTTPException(
            detail="Min is greater than max.", status_code=HTTPStatus.BAD_REQUEST
        )

    if data.currency is None and (
        round(data.min) != data.min or round(data.max) != data.max or data.min < 1
    ):
        raise HTTPException(
            detail="Must use full satoshis.", status_code=HTTPStatus.BAD_REQUEST
        )

    if data.webhook_headers:
        try:
            json.loads(data.webhook_headers)
        except ValueError as exc:
            raise HTTPException(
                detail="Invalid JSON in webhook_headers.",
                status_code=HTTPStatus.BAD_REQUEST,
            ) from exc

    if data.webhook_body:
        try:
            json.loads(data.webhook_body)
        except ValueError as exc:
            raise HTTPException(
                detail="Invalid JSON in webhook_body.",
                status_code=HTTPStatus.BAD_REQUEST,
            ) from exc

    # database only allows int4 entries for min and max. For fiat currencies,
    # we multiply by data.fiat_base_multiplier (usually 100) to save the value in cents.
    if data.currency and data.fiat_base_multiplier:
        data.min *= data.fiat_base_multiplier
        data.max *= data.fiat_base_multiplier

    if (
        data.success_url
        and data.success_url != ""
        and not data.success_url.startswith("https://")
    ):
        raise HTTPException(
            detail="Success URL must be secure https://...",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    if data.username and not re.match("^[a-z0-9-_.]{1,210}$", data.username):
        raise HTTPException(
            detail=f"Invalid username: {data.username}. "
            "Only letters a-z0-9-_. allowed, min 1 and max 210 characters!",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    # if wallet is not provided, use the wallet of the key
    if not data.wallet:
        data.wallet = key_info.wallet.id

    new_wallet = await get_wallet(data.wallet)
    if not new_wallet:
        raise HTTPException(
            detail="Wallet does not exist.", status_code=HTTPStatus.FORBIDDEN
        )

    # admins are allowed to create/edit paylinks beloging to regular users
    user = await get_user(key_info.wallet.user)
    admin_user = user.admin if user else False
    if not admin_user and new_wallet.user != key_info.wallet.user:
        raise HTTPException(
            detail="Not your pay link.", status_code=HTTPStatus.FORBIDDEN
        )

    if link_id:
        link = await get_pay_link(link_id)

        if not link:
            raise HTTPException(
                detail="Pay link does not exist.", status_code=HTTPStatus.NOT_FOUND
            )

        if data.username and data.username != link.username:
            await check_username_exists(data.username)

        for k, v in data.dict().items():
            setattr(link, k, v)

        link = await update_pay_link(link)
    else:
        if data.username:
            await check_username_exists(data.username)

        link = await create_pay_link(data)

    assert link
    return {**link.dict(), "lnurl": link.lnurl(request)}


@lnurlp_api_router.delete("/api/v1/links/{link_id}", status_code=HTTPStatus.OK)
async def api_link_delete(
    link_id: str, key_info: WalletTypeInfo = Depends(require_admin_key)
):
    link = await get_pay_link(link_id)

    if not link:
        raise HTTPException(
            detail="Pay link does not exist.", status_code=HTTPStatus.NOT_FOUND
        )

    # admins are allowed to delete paylinks beloging to regular users
    user = await get_user(key_info.wallet.user)
    admin_user = user.admin if user else False
    if not admin_user and link.wallet != key_info.wallet.id:
        raise HTTPException(
            detail="Not your pay link.", status_code=HTTPStatus.FORBIDDEN
        )

    await delete_pay_link(link_id)
    return {"success": True}


@lnurlp_api_router.get("/api/v1/rate/{currency}", status_code=HTTPStatus.OK)
async def api_check_fiat_rate(currency):
    try:
        rate = await get_fiat_rate_satoshis(currency)
    except AssertionError:
        rate = None

    return {"rate": rate}


@lnurlp_api_router.get("/api/v1/settings", dependencies=[Depends(check_admin)])
async def api_get_or_create_settings() -> LnurlpSettings:
    return await get_or_create_lnurlp_settings()


@lnurlp_api_router.put("/api/v1/settings", dependencies=[Depends(check_admin)])
async def api_update_settings(data: LnurlpSettings) -> LnurlpSettings:
    try:
        parse_nostr_private_key(data.nostr_private_key)
    except Exception as exc:
        raise HTTPException(
            detail="Invalid Nostr private key.", status_code=HTTPStatus.BAD_REQUEST
        ) from exc
    return await update_lnurlp_settings(data)


@lnurlp_api_router.delete("/api/v1/settings", dependencies=[Depends(check_admin)])
async def api_delete_settings() -> None:
    await delete_lnurlp_settings()
