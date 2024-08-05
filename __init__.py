import asyncio
from typing import List

from fastapi import APIRouter

from .crud import db
from .tasks import wait_for_paid_invoices
from .views import lnurlp_generic_router
from .views_api import lnurlp_api_router
from .views_lnurl import lnurlp_lnurl_router

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


lnurlp_ext: APIRouter = APIRouter(prefix="/lnurlp", tags=["lnurlp"])
lnurlp_ext.include_router(lnurlp_generic_router)
lnurlp_ext.include_router(lnurlp_api_router)
lnurlp_ext.include_router(lnurlp_lnurl_router)

scheduled_tasks: List[asyncio.Task] = []


def lnurlp_stop():
    for task in scheduled_tasks:
        task.cancel()


def lnurlp_start():
    from lnbits.tasks import create_permanent_unique_task

    task = create_permanent_unique_task("lnurlp", wait_for_paid_invoices)
    scheduled_tasks.append(task)


__all__ = [
    "lnurlp_ext",
    "lnurlp_static_files",
    "lnurlp_redirect_paths",
    "lnurlp_stop",
    "lnurlp_start",
    "db",
]
