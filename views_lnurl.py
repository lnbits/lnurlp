import json
import re
from http import HTTPStatus
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Query, Request
from lnbits.core.crud.users import get_account_by_username, get_user_from_account
from lnbits.core.services import create_invoice
from lnbits.settings import settings
from lnbits.utils.exchange_rates import get_fiat_rate_satoshis
from lnurl import (
    CallbackUrl,
    LightningInvoice,
    LnurlErrorResponse,
    LnurlPayActionResponse,
    LnurlPayMetadata,
    LnurlPayResponse,
    LnurlPaySuccessActionTag,
    Max144Str,
    MessageAction,
    MilliSatoshi,
    UrlAction,
)
from pydantic import parse_obj_as
from sqlalchemy.exc import IntegrityError  # type: ignore[import-untyped]

from .crud import (
    create_pay_link,
    get_address_data,
    get_or_create_lnurlp_settings,
    get_pay_link,
    update_pay_link,
)
from .models import CreatePayLinkData, PayLink

lnurlp_lnurl_router = APIRouter()

_LNADDRESS_USERNAME_PATTERN = r"^[a-z0-9-_.]{1,210}$"
_MAX_DATABASE_SATS = 2_147_483_647


def configured_lnaddress_domain() -> str | None:
    parsed = urlsplit(settings.lnbits_baseurl)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None

    try:
        port = parsed.port
    except ValueError:
        return None

    hostname = parsed.hostname.encode("idna").decode("ascii").lower()
    if port and not (
        (parsed.scheme == "http" and port == 80)
        or (parsed.scheme == "https" and port == 443)
    ):
        return f"{hostname}:{port}"
    return hostname


async def create_default_lnaddress(username: str) -> PayLink | None:
    account = await get_account_by_username(username)
    if not account or not account.username:
        return None

    username = account.username.lower()
    if not re.fullmatch(_LNADDRESS_USERNAME_PATTERN, username):
        return None

    existing_link = await get_address_data(username)
    if existing_link:
        return existing_link

    domain = configured_lnaddress_domain()
    if not domain:
        return None

    user = await get_user_from_account(account)
    if not user:
        return None
    wallet = next(
        (wallet for wallet in user.wallets if wallet.can_receive_payments), None
    )
    if not wallet:
        return None

    maximum = min(
        settings.lnbits_max_incoming_payment_amount_sats or _MAX_DATABASE_SATS,
        _MAX_DATABASE_SATS,
    )
    try:
        return await create_pay_link(
            CreatePayLinkData(
                description=f"Payment to {username}",
                wallet=wallet.id,
                min=1,
                max=maximum,
                username=username,
                zaps=True,
                disposable=False,
                domain=domain,
            )
        )
    except IntegrityError:
        link = await get_address_data(username)
        if link:
            return link
        raise


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
) -> LnurlErrorResponse | LnurlPayActionResponse:
    link = await get_pay_link(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )
    link.served_pr = 1
    await update_pay_link(link)
    minimum = link.min
    maximum = link.max

    rate = await get_fiat_rate_satoshis(link.currency) if link.currency else 1
    if link.currency and link.fiat_base_multiplier:
        link.min = link.min / link.fiat_base_multiplier
        link.max = link.max / link.fiat_base_multiplier
        # allow some fluctuation (as the fiat price may have changed between the calls)
        minimum = rate * 995 * link.min
        maximum = rate * 1010 * link.max
    else:
        minimum = link.min * 1000
        maximum = link.max * 1000

    amount = amount
    if amount < minimum:
        return LnurlErrorResponse(
            reason=f"Amount {amount} is smaller than minimum {minimum}."
        )

    elif amount > maximum:
        return LnurlErrorResponse(
            reason=f"Amount {amount} is greater than maximum {maximum}."
        )

    comment = request.query_params.get("comment")
    if len(comment or "") > link.comment_chars:
        return LnurlErrorResponse(
            reason=(
                f"Got a comment with {len(comment or '')} characters, "
                f"but can only accept {link.comment_chars}"
            )
        )

    extra = {
        "tag": "lnurlp",
        "link": link.id,
        "extra": request.query_params.get("amount"),
    }

    if comment:
        extra["comment"] = comment

    if webhook_data:
        extra["webhook_data"] = webhook_data

    # nip 57
    nostr = request.query_params.get("nostr")
    if nostr:
        extra["nostr"] = nostr  # put it here for later publishing in tasks.py

    if link.username:
        identifier = f"{link.username}@{link.domain or request.url.netloc}"
        text = f"Payment to {link.username}"
        _metadata = [["text/plain", text], ["text/identifier", identifier]]
        extra["lnaddress"] = identifier
    else:
        _metadata = [["text/plain", link.description]]

    metadata = LnurlPayMetadata(json.dumps(_metadata))

    # we take the zap request as the description instead of the metadata if present
    unhashed_description = nostr.encode() if nostr else metadata.encode()

    payment = await create_invoice(
        wallet_id=link.wallet,
        amount=int(amount / 1000),
        memo=link.description,
        unhashed_description=unhashed_description,
        extra=extra,
    )
    invoice = parse_obj_as(LightningInvoice, LightningInvoice(payment.bolt11))

    if link.success_url:
        url = parse_obj_as(CallbackUrl, str(link.success_url))
        text = link.success_text or f"Link to {link.success_url}"
        desc = parse_obj_as(Max144Str, text)
        action = UrlAction(tag=LnurlPaySuccessActionTag.url, url=url, description=desc)
        return LnurlPayActionResponse(
            pr=invoice, successAction=action, disposable=link.disposable
        )

    if link.success_text:
        message = parse_obj_as(Max144Str, link.success_text)
        return LnurlPayActionResponse(
            pr=invoice,
            successAction=MessageAction(message=message),
            disposable=link.disposable,
        )

    return LnurlPayActionResponse(pr=invoice, disposable=link.disposable)


@lnurlp_lnurl_router.get(
    "/api/v1/lnurl/{link_id}",  # Backwards compatibility for old LNURLs / QR codes
    name="lnurlp.api_lnurl_response.deprecated",
    deprecated=True,
)
@lnurlp_lnurl_router.get(
    "/{link_id}",
    name="lnurlp.api_lnurl_response",
)
async def api_lnurl_response(
    request: Request,
    link_id: str,
    webhook_data: Annotated[str | None, Query()] = None,
) -> LnurlPayResponse:
    link = await get_pay_link(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )
    link.served_meta = 1
    await update_pay_link(link)

    rate = await get_fiat_rate_satoshis(link.currency) if link.currency else 1

    if link.currency and link.fiat_base_multiplier:
        link.min = link.min / link.fiat_base_multiplier
        link.max = link.max / link.fiat_base_multiplier

    url = request.url_for("lnurlp.api_lnurl_callback", link_id=link.id)
    if webhook_data:
        url = url.include_query_params(webhook_data=webhook_data)

    callback_url = parse_obj_as(CallbackUrl, str(url))

    if link.username:
        identifier = f"{link.username}@{link.domain or request.url.netloc}"
        text = f"Payment to {link.username}"
        metadata = [["text/plain", text], ["text/identifier", identifier]]
    else:
        metadata = [["text/plain", link.description]]

    res = LnurlPayResponse(
        callback=callback_url,
        minSendable=MilliSatoshi(round(link.min * rate) * 1000),
        maxSendable=MilliSatoshi(round(link.max * rate) * 1000),
        metadata=LnurlPayMetadata(json.dumps(metadata)),
    )

    if link.comment_chars > 0:
        res.commentAllowed = link.comment_chars

    if link.zaps:
        settings = await get_or_create_lnurlp_settings()
        res.allowsNostr = True
        res.nostrPubkey = settings.public_key

    return res


# redirected from /.well-known/lnurlp
@lnurlp_lnurl_router.get("/api/v1/well-known/{username}")
async def lnaddress(
    username: str, request: Request
) -> LnurlPayResponse | LnurlErrorResponse:
    address_data = await get_address_data(username)
    if not address_data:
        address_data = await create_default_lnaddress(username)
    if not address_data:
        return LnurlErrorResponse(reason="Lightning address not found.")
    return await api_lnurl_response(request, address_data.id)
