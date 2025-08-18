import json
from datetime import datetime, timezone

from fastapi import Query, Request
from lnbits.helpers import normalize_path
from lnurl import encode as lnurl_encode
from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel, Field

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
    wallet: str | None = None
    min: float = Query(1, ge=0.01)
    max: float = Query(1, ge=0.01)
    comment_chars: int = Query(0, ge=0, le=799)
    currency: str | None = Query(None)
    webhook_url: str | None = Query(None)
    webhook_headers: str | None = Query(None)
    webhook_body: str | None = Query(None)
    success_text: str | None = Query(None)
    success_url: str | None = Query(None)
    fiat_base_multiplier: int | None = Query(100, ge=1)
    username: str | None = Query(None)
    zaps: bool | None = Query(False)
    disposable: bool | None = Query(True)


class PayLink(BaseModel):
    id: str
    wallet: str
    description: str
    min: float
    max: float
    served_meta: int
    served_pr: int
    comment_chars: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    username: str | None = None
    zaps: bool | None = None
    domain: str | None = None
    webhook_url: str | None = None
    webhook_headers: str | None = None
    webhook_body: str | None = None
    success_text: str | None = None
    success_url: str | None = None
    currency: str | None = None
    fiat_base_multiplier: int | None = None

    disposable: bool

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
