from fastapi import APIRouter

from app.tool_registry import public_tools

router = APIRouter()


@router.get("/")
async def list_tools():
    return {"tools": public_tools()}
