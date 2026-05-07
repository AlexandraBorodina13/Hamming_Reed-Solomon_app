from fastapi import APIRouter
from app.models.requests import BCHEncodeRequest, BCHDecodeRequest
from app.models.responses import EncodeResponse, DecodeResponse
from app.services.decoding_service import BCHService

router = APIRouter(prefix="/bch", tags=["BCH"])

@router.post("/encode", response_model=EncodeResponse)
def encode(req: BCHEncodeRequest):
    return BCHService.encode(req.n, req.k, req.message)

@router.post("/decode", response_model=DecodeResponse)
def decode(req: BCHDecodeRequest):
    return BCHService.decode(req.n, req.k, req.received)