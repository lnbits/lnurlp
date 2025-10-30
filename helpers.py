from fastapi import Request
from lnurl import encode as lnurl_encode
from pynostr.key import PrivateKey


def parse_nostr_private_key(key: str) -> PrivateKey:
    if key.startswith("nsec"):
        return PrivateKey.from_nsec(key)
    else:
        return PrivateKey(bytes.fromhex(key))


def lnurl_encode_link_id(req: Request, link_id: str) -> str:
    url = req.url_for("lnurlp.api_lnurl_response", link_id=link_id)
    url = url.replace(path=url.path)
    url_str = str(url)
    if url.netloc.endswith(".onion"):
        # change url string scheme to http
        url_str = url_str.replace("https://", "http://")
    return str(lnurl_encode(url_str).bech32)
