from fastapi import APIRouter, Depends
from lnbits.core.views.generic import index, index_public
from lnbits.decorators import check_user_exists

lnurlp_generic_router = APIRouter()

lnurlp_generic_router.add_api_route(
    "/", methods=["GET"], endpoint=index, dependencies=[Depends(check_user_exists)]
)

lnurlp_generic_router.add_api_route(
    "/link/{link_id}", methods=["GET"], endpoint=index_public
)

lnurlp_generic_router.add_api_route(
    "/print/{link_id}", methods=["GET"], endpoint=index_public
)
