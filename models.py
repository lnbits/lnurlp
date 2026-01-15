from datetime import datetime, timezone

from fastapi import Query
from pydantic import BaseModel, Field
from pynostr.key import PrivateKey

from .helpers import parse_nostr_private_key


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
    domain: str | None = Query(None)


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
    lnurl: str | None = Field(
        default=None,
        no_database=True,
        deprecated=True,
        description=(
            "Deprecated: Instead of using this bech32 encoded string, dynamically "
            "generate your own static link (lud17/bech32) on the client side. "
            "Example: lnurlp://${window.location.hostname}/lnurlp/${paylink_id}"
        ),
    )
    username: str | None = None
    zaps: bool | None = None
    webhook_url: str | None = None
    webhook_headers: str | None = None
    webhook_body: str | None = None
    success_text: str | None = None
    success_url: str | None = None
    currency: str | None = None
    fiat_base_multiplier: int | None = None
    disposable: bool
    domain: str | None = None


class PublicPayLink(BaseModel):
    id: str
    username: str | None = None
    description: str
    min: float
    max: float
    domain: str | None = None
    currency: str | None = None
    lnurl: str | None = Field(
        default=None,
        no_database=True,
        deprecated=True,
        description=(
            "Deprecated: Instead of using this bech32 encoded string, dynamically "
            "generate your own static link (lud17/bech32) on the client side. "
            "Example: lnurlp://${window.location.hostname}/lnurlp/${paylink_id}"
        ),
    )
