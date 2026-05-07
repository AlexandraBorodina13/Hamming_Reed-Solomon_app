from fastapi import APIRouter
from app.models.requests import HammingEncodeRequest, HammingDecodeRequest
from app.models.responses import EncodeResponse, DecodeResponse
from app.services.decoding_service import HammingService

router = APIRouter(prefix="/hamming", tags=["Hamming"])

@router.post("/encode", response_model=EncodeResponse)
def encode(req: HammingEncodeRequest):
    result = HammingService.encode(req.m, req.message)
    n = 2**req.m - 1
    k = n - req.m
    return EncodeResponse(codeword=result["codeword"], params={"n": n, "k": k, "m": req.m})

@router.post("/decode", response_model=DecodeResponse)
def decode(req: HammingDecodeRequest):
    return HammingService.decode(req.m, req.received)