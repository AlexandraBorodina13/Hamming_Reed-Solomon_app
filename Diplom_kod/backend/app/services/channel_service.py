import numpy as np
from app.core.channels import awgn_channel

class ChannelService:
    @staticmethod
    def apply_awgn(bits_str: str, snr_db: float, n: int = None, k: int = None) -> str:
        bits = np.array([int(c) for c in bits_str], dtype=int)
        noisy = awgn_channel(bits, snr_db, k=k, n=n)
        return ''.join(str(b) for b in noisy)