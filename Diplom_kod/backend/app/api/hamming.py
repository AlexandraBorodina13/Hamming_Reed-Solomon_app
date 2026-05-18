from fastapi import APIRouter
from app.models.requests import HammingEncodeRequest, HammingDecodeRequest
from app.models.responses import EncodeResponse, DecodeResponse
from app.services.decoding_service import HammingService

router = APIRouter(prefix="/hamming", tags=["Hamming"])

@router.post("/encode", response_model=EncodeResponse)
def encode(req: HammingEncodeRequest):
    return HammingService.encode(req.m, req.message)

@router.post("/decode", response_model=DecodeResponse)
def decode(req: HammingDecodeRequest):
    return HammingService.decode(req.m, req.received, req.original_message)