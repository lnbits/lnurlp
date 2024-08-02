from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Query, Request
from lnbits.core.services import create_invoice
from lnbits.utils.exchange_rates import get_fiat_rate_satoshis
from lnurl import LnurlErrorResponse, LnurlPayActionResponse, LnurlPayResponse
from starlette.exceptions import HTTPException

from .crud import (
    get_address_data,
    get_or_create_lnurlp_settings,
    increment_pay_link,
)

lnurlp_lnurl_router = APIRouter()


@lnurlp_lnurl_router.get(
    "/api/v1/lnurl/cb/{link_id}",
    status_code=HTTPStatus.OK,
    name="lnurlp.api_lnurl_callback",
)
async def api_lnurl_callback(
    request: Request,
    link_id: str,
    amount: int = Query(...),
    webhook_data: str = Query(None),
):
    link = await increment_pay_link(link_id, served_pr=1)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )
    mininum = link.min
    maximum = link.max

    rate = await get_fiat_rate_satoshis(link.currency) if link.currency else 1
    if link.currency:
        # allow some fluctuation (as the fiat price may have changed between the calls)
        mininum = rate * 995 * link.min
        maximum = rate * 1010 * link.max
    else:
        mininum = link.min * 1000
        maximum = link.max * 1000

    amount = amount
    if amount < mininum:
        return LnurlErrorResponse(
            reason=f"Amount {amount} is smaller than minimum {min}."
        ).dict()

    elif amount > maximum:
        return LnurlErrorResponse(
            reason=f"Amount {amount} is greater than maximum {max}."
        ).dict()

    comment = request.query_params.get("comment")
    if len(comment or "") > link.comment_chars:
        return LnurlErrorResponse(
            reason=(
                f"Got a comment with {len(comment or '')} characters, "
                f"but can only accept {link.comment_chars}"
            )
        ).dict()

    # for lnaddress, we have to set this otherwise
    # the metadata won't have the identifier
    link.domain = request.url.netloc

    extra = {
        "tag": "lnurlp",
        "link": link.id,
        "extra": request.query_params.get("amount"),
    }

    if comment:
        extra["comment"] = (comment,)

    if webhook_data:
        extra["webhook_data"] = webhook_data

    # nip 57
    nostr = request.query_params.get("nostr")
    if nostr:
        extra["nostr"] = nostr  # put it here for later publishing in tasks.py

    if link.username and link.domain:
        extra["lnaddress"] = f"{link.username}@{link.domain}"

    # we take the zap request as the description instead of the metadata if present
    unhashed_description = nostr.encode() if nostr else link.lnurlpay_metadata.encode()

    payment_hash, payment_request = await create_invoice(
        wallet_id=link.wallet,
        amount=int(amount / 1000),
        memo=link.description,
        unhashed_description=unhashed_description,
        extra=extra,
    )

    success_action = link.success_action(payment_hash)
    if success_action:
        resp = LnurlPayActionResponse(
            pr=payment_request, success_action=success_action, routes=[]
        )
    else:
        resp = LnurlPayActionResponse(pr=payment_request, routes=[])

    return resp.dict()


@lnurlp_lnurl_router.get(
    "/api/v1/lnurl/{link_id}",  # Backwards compatibility for old LNURLs / QR codes
    status_code=HTTPStatus.OK,
    name="lnurlp.api_lnurl_response.deprecated",
)
@lnurlp_lnurl_router.get(
    "/{link_id}",
    status_code=HTTPStatus.OK,
    name="lnurlp.api_lnurl_response",
)
async def api_lnurl_response(
    request: Request, link_id, webhook_data: Optional[str] = Query(None)
):
    link = await increment_pay_link(link_id, served_meta=1)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )

    rate = await get_fiat_rate_satoshis(link.currency) if link.currency else 1
    url = request.url_for("lnurlp.api_lnurl_callback", link_id=link.id)
    if webhook_data:
        url = url.include_query_params(webhook_data=webhook_data)

    link.domain = request.url.netloc

    resp = LnurlPayResponse(
        callback=str(url),
        min_sendable=round(link.min * rate) * 1000,
        max_sendable=round(link.max * rate) * 1000,
        metadata=link.lnurlpay_metadata,
    )
    params = resp.dict()

    if link.comment_chars > 0:
        params["commentAllowed"] = link.comment_chars

    if link.zaps:
        settings = await get_or_create_lnurlp_settings()
        params["allowsNostr"] = True
        params["nostrPubkey"] = settings.public_key
    return params


# redirected from /.well-known/lnurlp
@lnurlp_lnurl_router.get("/api/v1/well-known/{username}")
async def lnaddress(username: str, request: Request):
    address_data = await get_address_data(username)
    assert address_data, "User not found"
    return await api_lnurl_response(request, address_data.id, webhook_data=None)
