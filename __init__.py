import asyncio
from typing import List

from fastapi import APIRouter

from lnbits.db import Database
from lnbits.helpers import template_renderer
from lnbits.tasks import catch_everything_and_restart
from loguru import logger


from .nostr.event import Event
from .nostr.key import PrivateKey, PublicKey
from environs import Env


def generate_keys(private_key: str = ""):
    if private_key.startswith("nsec"):
        return PrivateKey.from_nsec(private_key)
    elif private_key:
        return PrivateKey(bytes.fromhex(private_key))
    else:
        return PrivateKey()  # generate random key


env = Env()
env.read_env()
nostr_privatekey = generate_keys(env.str("LNURLP_ZAP_NOSTR_PRIVATEKEY", default=""))
nostr_publickey: PublicKey = nostr_privatekey.public_key
logger.debug(f"LNURLP Zaps Nostr pubkey: {nostr_publickey.hex()}")

db = Database("ext_lnurlp")

lnurlp_static_files = [
    {
        "path": "/lnurlp/static",
        "name": "lnurlp_static",
    }
]

lnurlp_redirect_paths = [
    {
        "from_path": "/.well-known/lnurlp",
        "redirect_to_path": "/api/v1/well-known",
    }
]

scheduled_tasks: List[asyncio.Task] = []

lnurlp_ext: APIRouter = APIRouter(prefix="/lnurlp", tags=["lnurlp"])


def lnurlp_renderer():
    return template_renderer(["lnurlp/templates"])


from .lnurl import *  # noqa: F401,F403
from .tasks import wait_for_paid_invoices
from .views import *  # noqa: F401,F403
from .views_api import *  # noqa: F401,F403


def lnurlp_start():
    loop = asyncio.get_event_loop()
    task = loop.create_task(catch_everything_and_restart(wait_for_paid_invoices))
    scheduled_tasks.append(task)
