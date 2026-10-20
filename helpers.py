import asyncio
import ipaddress
import json
import socket
from urllib.parse import urlsplit

from fastapi import Request
from lnbits.helpers import check_callback_url
from lnbits.settings import settings
from lnurl import encode as lnurl_encode
from pynostr.event import Event
from pynostr.key import PrivateKey


def parse_nostr_private_key(key: str) -> PrivateKey:
    if key.startswith("nsec"):
        return PrivateKey.from_nsec(key)
    else:
        return PrivateKey(bytes.fromhex(key))


def lnurl_encode_link(req: Request, link_id: str, domain: str | None = None) -> str:
    if domain:
        url_str = f"https://{domain}/lnurlp/{link_id}"
        return str(lnurl_encode(url_str).bech32)

    url = req.url_for("lnurlp.api_lnurl_response", link_id=link_id)
    url = url.replace(path=url.path)
    url_str = str(url)
    if url.netloc.endswith(".onion"):
        # change url string scheme to http
        url_str = url_str.replace("https://", "http://")

    return str(lnurl_encode(url_str).bech32)


async def resolve_callback_addresses(url: str) -> list[str]:
    parsed = urlsplit(url)
    scheme = {"ws": "http", "wss": "https"}.get(parsed.scheme, parsed.scheme)
    check_callback_url(parsed._replace(scheme=scheme).geturl())
    port = parsed.port or (443 if scheme == "https" else 80)
    try:
        infos = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(
                parsed.hostname, port, type=socket.SOCK_STREAM
            ),
            timeout=5,
        )
    except (OSError, asyncio.TimeoutError) as exc:
        raise ValueError("Callback target could not be resolved.") from exc
    addresses = [ipaddress.ip_address(info[4][0]) for info in infos]
    if not addresses or (
        not settings.lnbits_callback_allow_private_ips
        and any(not address.is_global for address in addresses)
    ):
        raise ValueError("Callback target IP address is not allowed.")
    return [str(address) for address in dict.fromkeys(addresses)]


def validate_zap_request(nostr: str, amount: int, nostr_pubkey: str) -> Event:
    try:
        if len(nostr.encode()) > 16384:
            raise ValueError("Zap request is too large.")
        data = json.loads(nostr)
        tags = data["tags"]
        if (
            data["kind"] != 9734
            or not isinstance(data["content"], str)
            or type(data["created_at"]) is not int
            or data["created_at"] < 0
            or not _is_hex_key(data["pubkey"])
            or not isinstance(tags, list)
            or not 1 <= len(tags) <= 128
            or any(
                not isinstance(tag, list)
                or len(tag) < 2
                or any(not isinstance(value, str) or len(value) > 2048 for value in tag)
                for tag in tags
            )
        ):
            raise ValueError("Invalid zap request tags or kind.")

        for name in ("p", "e", "a", "amount", "relays", "P"):
            values = [tag[1:] for tag in tags if tag[0] == name]
            if len(values) > 1 or (name in {"p", "relays"} and not values):
                raise ValueError("Invalid zap request tags.")
            if not values:
                continue
            value = values[0][0]
            if name in {"p", "e", "P"} and not _is_hex_key(value):
                raise ValueError("Invalid zap request public key or event id.")
            if name == "P" and value != nostr_pubkey:
                raise ValueError("Zap request targets a different provider.")
            if name == "amount" and int(value) != amount:
                raise ValueError("Zap request amount does not match.")
            if name == "a":
                coordinate = value.split(":", 2)
                if (
                    len(coordinate) != 3
                    or not coordinate[0].isdigit()
                    or not 0 <= int(coordinate[0]) <= 65535
                    or not _is_hex_key(coordinate[1])
                ):
                    raise ValueError("Invalid zap request event coordinate.")
            if name == "relays":
                for relay in values[0][:50]:
                    parsed = urlsplit(relay)
                    if parsed.scheme not in {"ws", "wss"}:
                        raise ValueError("Invalid zap relay scheme.")
                    scheme = "https" if parsed.scheme == "wss" else "http"
                    check_callback_url(parsed._replace(scheme=scheme).geturl())

        event = Event.from_dict(data)
        if not event.verify() or data.get("id") != event.id:
            raise ValueError("Invalid zap request signature.")
        return event
    except (
        ValueError,
        KeyError,
        TypeError,
        AssertionError,
        IndexError,
        RecursionError,
    ) as exc:
        raise ValueError("Invalid zap request.") from exc


def _is_hex_key(value: str) -> bool:
    try:
        return len(value) == 64 and len(bytes.fromhex(value)) == 32
    except ValueError:
        return False
