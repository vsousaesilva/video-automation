import asyncio
import os

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from core.auth import require_role

router = APIRouter(prefix="/admin", tags=["admin"])

DEPLOY_SCRIPT = "/home/usina/deploy.sh"


@router.post("/deploy")
async def trigger_deploy(current_user: dict = Depends(require_role(["admin"]))):
    if not os.path.isfile(DEPLOY_SCRIPT):
        return {"status": "error", "log": f"Script não encontrado: {DEPLOY_SCRIPT}"}

    async def stream_output():
        proc = await asyncio.create_subprocess_exec(
            "bash", DEPLOY_SCRIPT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        async for line in proc.stdout:
            yield line.decode("utf-8", errors="replace")
        await proc.wait()
        yield f"\n=== Exit code: {proc.returncode} ===\n"

    return StreamingResponse(stream_output(), media_type="text/plain")
