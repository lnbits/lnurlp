import json
from datetime import datetime
from typing import Optional

from fastapi import Query, Request
from lnbits.helpers import normalize_path
from lnurl import encode as lnurl_encode
from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel

from .helpers import parse_nostr_private_key
from .nostr.key import PrivateKey


class LnurlpSettings(BaseModel):
    nostr_private_key: str

    @property
    def private_key(self) -> PrivateKey:
        return parse_nostr_private_key(self.nostr_private_key)

    @property
    def public_key(self) -> str:
        return self.private_key.public_key.hex()


class CreatePayLinkData(BaseModel):
    description: str
    wallet: Optional[str] = None
    min: float = Query(1, ge=0.01)
    max: float = Query(1, ge=0.01)
    currency: str = Query(None)
    comment_chars: int = Query(0, ge=0, le=799)
    webhook_url: str = Query(None)
    webhook_headers: str = Query(None)
    webhook_body: str = Query(None)
    success_text: str = Query(None)
    success_url: str = Query(None)
    fiat_base_multiplier: int = Query(100, ge=1)
    username: str = Query(None)
    zaps: Optional[bool] = Query(False)


class PayLink(BaseModel):
    id: str
    wallet: str
    description: str
    min: float
    served_meta: int
    served_pr: int
    username: Optional[str]
    zaps: Optional[bool]
    domain: Optional[str]
    webhook_url: Optional[str]
    webhook_headers: Optional[str]
    webhook_body: Optional[str]
    success_text: Optional[str]
    success_url: Optional[str]
    currency: Optional[str]
    comment_chars: int
    max: float
    fiat_base_multiplier: int
    created_at: datetime
    updated_at: datetime

    def lnurl(self, req: Request) -> str:
        url = req.url_for("lnurlp.api_lnurl_response", link_id=self.id)
        url = url.replace(path=normalize_path(url.path))
        url_str = str(url)
        if url.netloc.endswith(".onion"):
            # change url string scheme to http
            url_str = url_str.replace("https://", "http://")

        return lnurl_encode(url_str)

    @property
    def lnurlpay_metadata(self) -> LnurlPayMetadata:
        if self.domain and self.username:
            text = f"Payment to {self.username}"
            identifier = f"{self.username}@{self.domain}"
            metadata = [["text/plain", text], ["text/identifier", identifier]]
        else:
            metadata = [["text/plain", self.description]]

        return LnurlPayMetadata(json.dumps(metadata))
