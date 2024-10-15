from http import HTTPStatus

from fastapi import APIRouter, Depends, Request
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse

from .crud import get_pay_link

lnurlp_generic_router = APIRouter()


def lnurlp_renderer():
    return template_renderer(["lnurlp/templates"])


@lnurlp_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return lnurlp_renderer().TemplateResponse(
        "lnurlp/index.html", {"request": request, "user": user.json()}
    )


@lnurlp_generic_router.get("/link/{link_id}", response_class=HTMLResponse)
async def display(request: Request, link_id):
    link = await get_pay_link(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )
    ctx = {"request": request, "lnurl": link.lnurl(req=request)}
    return lnurlp_renderer().TemplateResponse("lnurlp/display.html", ctx)


@lnurlp_generic_router.get("/print/{link_id}", response_class=HTMLResponse)
async def print_qr(request: Request, link_id):
    link = await get_pay_link(link_id)
    if not link:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Pay link does not exist."
        )
    ctx = {"request": request, "lnurl": link.lnurl(req=request)}
    return lnurlp_renderer().TemplateResponse("lnurlp/print_qr.html", ctx)
