from http import HTTPStatus

from fastapi import Request, Query
from lnurl import LnurlErrorResponse, LnurlPayActionResponse, LnurlPayResponse
from starlette.exceptions import HTTPException

from lnbits.core.services import create_invoice
from lnbits.utils.exchange_rates import get_fiat_rate_satoshis

from . import lnurlp_ext
from .crud import increment_pay_link, get_pay_link, get_address_data
from loguru import logger
from urllib.parse import urlparse
import json


@lnurlp_ext.get(
    "/api/v1/lnurl/cb/lnaddr/{link_id}",
    status_code=HTTPStatus.OK,
    name="lnurlp.api_lnurl_lnaddr_callback",
)
async def api_lnurl_lnaddr_callback(
    request: Request, link_id, amount: int = Query(...)
):
    return await api_lnurl_callback(request, link_id, amount, lnaddress=True)


@lnurlp_ext.get(
    "/api/v1/lnurl/cb/{link_id}",
    status_code=HTTPStatus.OK,
    name="lnurlp.api_lnurl_callback",
)
async def api_lnurl_callback(
    request: Request, link_id, amount: int = Query(...), lnaddress=False
):
    link = await increment_pay_link(link_id, served_pr=1)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )
    min, max = link.min, link.max
    rate = await get_fiat_rate_satoshis(link.currency) if link.currency else 1
    if link.currency:
        # allow some fluctuation (as the fiat price may have changed between the calls)
        min = rate * 995 * link.min
        max = rate * 1010 * link.max
    else:
        min = link.min * 1000
        max = link.max * 1000

    amount_received = amount
    if amount_received < min:
        return LnurlErrorResponse(
            reason=f"Amount {amount_received} is smaller than minimum {min}."
        ).dict()

    elif amount_received > max:
        return LnurlErrorResponse(
            reason=f"Amount {amount_received} is greater than maximum {max}."
        ).dict()

    comment = request.query_params.get("comment")
    if len(comment or "") > link.comment_chars:
        return LnurlErrorResponse(
            reason=f"Got a comment with {len(comment)} characters, but can only accept {link.comment_chars}"
        ).dict()

    if lnaddress:
        # for lnaddress, we have to set this otherwise the metadata won't have the identifier
        link.domain = urlparse(str(request.url)).netloc

    extra = {
        "tag": "lnurlp",
        "link": link.id,
        "extra": request.query_params.get("amount"),
    }

    if comment:
        extra["comment"] = (comment,)

    nostr = request.query_params.get("nostr")
    if nostr:
        extra["nostr"] = nostr

    if lnaddress and link.username and link.domain:
        extra["lnaddress"] = f"{link.username}@{link.domain}"

    payment_hash, payment_request = await create_invoice(
        wallet_id=link.wallet,
        amount=int(amount_received / 1000),
        memo=link.description,
        unhashed_description=nostr.encode()
        if nostr
        else link.lnurlpay_metadata.encode(),
        extra=extra,
    )

    success_action = link.success_action(payment_hash)
    if success_action:
        resp = LnurlPayActionResponse(
            pr=payment_request, success_action=success_action, routes=[]  # type: ignore
        )
    else:
        resp = LnurlPayActionResponse(pr=payment_request, routes=[])  # type: ignore

    return resp.dict()


@lnurlp_ext.get(
    "/api/v1/lnurl/{link_id}",  # Backwards compatibility for old LNURLs / QR codes (with long URL)
    status_code=HTTPStatus.OK,
    name="lnurlp.api_lnurl_response.deprecated",
)
@lnurlp_ext.get(
    "/{link_id}",
    status_code=HTTPStatus.OK,
    name="lnurlp.api_lnurl_response",
)
async def api_lnurl_response(request: Request, link_id, lnaddress=False):
    link = await increment_pay_link(link_id, served_meta=1)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )

    rate = await get_fiat_rate_satoshis(link.currency) if link.currency else 1

    if lnaddress:
        # for lnaddress, we have to set this otherwise the metadata won't have the identifier
        link.domain = urlparse(str(request.url)).netloc
        callback = request.url_for("lnurlp.api_lnurl_lnaddr_callback", link_id=link.id)
    else:
        callback = request.url_for("lnurlp.api_lnurl_callback", link_id=link.id)

    resp = LnurlPayResponse(
        callback=callback,
        min_sendable=round(link.min * rate) * 1000,  # type: ignore
        max_sendable=round(link.max * rate) * 1000,  # type: ignore
        metadata=link.lnurlpay_metadata,
    )
    params = resp.dict()

    if link.comment_chars > 0:
        params["commentAllowed"] = link.comment_chars

    params["allowNostr"] = True
    params[
        "nostrPubkey"
    ] = "749b4d4dfc6b00a5e6c9a88d8a220c46c069ff8f027dcf312f040475e059554a"  # private: de1af06647137d49b2277faa86f96effc94257a7b7efd6f5dcc52bea08a4746b
    return params
