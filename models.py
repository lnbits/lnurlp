import json
from sqlite3 import Row
from typing import Dict, Optional
from urllib.parse import ParseResult, urlparse, urlunparse

from fastapi import Request
from fastapi.param_functions import Query
from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel

from lnbits.lnurl import encode as lnurl_encode


class CreatePayLinkData(BaseModel):
    description: str
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
    zaps: bool = Query(False)


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

    @classmethod
    def from_row(cls, row: Row) -> "PayLink":
        data = dict(row)
        if data["currency"] and data["fiat_base_multiplier"]:
            data["min"] /= data["fiat_base_multiplier"]
            data["max"] /= data["fiat_base_multiplier"]
        return cls(**data)

    def lnurl(self, req: Request) -> str:
        url = str(req.url_for("lnurlp.api_lnurl_response", link_id=self.id))
        # Check if url is .onion and change to http
        if urlparse(url).netloc.endswith(".onion"):
            # change url string scheme to http
            url = url.replace("https://", "http://")

        return lnurl_encode(url)

    def success_action(self, payment_hash: str) -> Optional[Dict]:
        if self.success_url:
            url: ParseResult = urlparse(self.success_url)
            # qs = parse_qs(url.query)
            # setattr(qs, "payment_hash", payment_hash)
            # url = url._replace(query=urlencode(qs, doseq=True))
            return {
                "tag": "url",
                "description": self.success_text or "~",
                "url": urlunparse(url),
            }
        elif self.success_text:
            return {"tag": "message", "message": self.success_text}
        else:
            return None

    @property
    def lnurlpay_metadata(self) -> LnurlPayMetadata:
        if self.domain and self.username:
            text = f"Payment to {self.username}"
            identifier = f"{self.username}@{self.domain}"
            metadata = [["text/plain", text], ["text/identifier", identifier]]
        else:
            metadata = [["text/plain", self.description]]

        return LnurlPayMetadata(json.dumps(metadata))
