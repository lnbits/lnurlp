from fastapi import APIRouter
from lnbits.task_manager import Task, task_manager  # type: ignore

from .crud import db
from .tasks import on_invoice_paid
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

scheduled_tasks: list[Task] = []


def lnurlp_stop():
    for task in scheduled_tasks:
        task_manager.cancel_task(task)


def lnurlp_start():
    task = task_manager.register_invoice_listener(on_invoice_paid, "ext_lnurlp")
    scheduled_tasks.append(task)


__all__ = [
    "db",
    "lnurlp_ext",
    "lnurlp_redirect_paths",
    "lnurlp_start",
    "lnurlp_static_files",
    "lnurlp_stop",
]
