from fastapi import APIRouter
from app.models.requests import AWGNRequest
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/channel", tags=["Channel"])

@router.post("/awgn")
def awgn_channel_endpoint(req: AWGNRequest):
    noisy = ChannelService.apply_awgn(req.bits, req.snr_db, req.n, req.k)
    return {"noisy_bits": noisy}
