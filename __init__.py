import asyncio
from typing import List

from fastapi import APIRouter

from lnbits.db import Database
from lnbits.helpers import template_renderer
from lnbits.tasks import create_permanent_unique_task


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
    create_permanent_unique_task("lnurlp", wait_for_paid_invoices)
