"""Public explorer shell. All data operations use the authenticated project API."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["explorer"])
ROOT = Path(__file__).parent
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
}


@router.get("/explorer", include_in_schema=False)
async def explorer():
    return FileResponse(ROOT / "index.html", headers=HEADERS)


@router.get("/explorer/{asset}", include_in_schema=False)
async def explorer_asset(asset: str):
    if asset not in ("explorer.js", "explorer.css"):
        raise HTTPException(404)
    return FileResponse(ROOT / asset, headers=HEADERS)
