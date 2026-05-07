from fastapi import APIRouter
from app.models.requests import ConvEncodeRequest, ConvDecodeRequest
from app.models.responses import EncodeResponse, DecodeResponse
from app.services.decoding_service import ConvolutionalService

router = APIRouter(prefix="/conv", tags=["Convolutional"])

@router.post("/encode", response_model=EncodeResponse)
def encode(req: ConvEncodeRequest):
    return ConvolutionalService.encode(req.preset, req.message)

@router.post("/decode", response_model=DecodeResponse)
def decode(req: ConvDecodeRequest):
    return ConvolutionalService.decode(req.preset, req.received)