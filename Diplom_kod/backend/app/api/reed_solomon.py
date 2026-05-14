from fastapi import APIRouter, BackgroundTasks
from app.models.requests import RSEncodeRequest, RSDecodeRequest
from app.models.responses import EncodeResponse
from app.services.decoding_service import RSService, tasks_db
from pydantic import BaseModel

router = APIRouter(prefix="/rs", tags=["Reed-Solomon"])

class TaskIdResponse(BaseModel):
    task_id: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None
    steps: list | None = None
    detail: str | None = None

@router.post("/encode", response_model=EncodeResponse)
def encode(req: RSEncodeRequest):
    return RSService.encode(req.preset, req.message)

@router.post("/decode/async", response_model=TaskIdResponse)
def decode_async(req: RSDecodeRequest, background_tasks: BackgroundTasks):
    task_id = RSService.decode_async(req.preset, req.received)
    background_tasks.add_task(RSService.perform_decode, task_id, req.preset, req.received)
    return {"task_id": task_id}

@router.get("/task/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    task = tasks_db.get(task_id)
    if not task:
        return {"task_id": task_id, "status": "not_found"}
    return {
        "task_id": task_id,
        "status": task["status"],
        "result": task.get("result"),
        "steps": task.get("steps"),
        "detail": task.get("detail"),
    }