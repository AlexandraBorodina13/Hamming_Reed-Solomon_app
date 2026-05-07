import numpy as np
from app.core.hamming import encode_general, decode_general
from app.explain.hamming_steps import explain_hamming_general
from app.models.responses import DecodeResponse, StepDTO

class HammingService:
    @staticmethod
    def encode(m: int, message: str) -> dict:
        bits = np.array([int(b) for b in message])
        codeword = encode_general(tuple(bits), m)
        return {"codeword": "".join(map(str, codeword))}

    @staticmethod
    def decode(m: int, received: str) -> DecodeResponse:
        bits = np.array([int(b) for b in received])
        corrected, info = decode_general(bits, m)
        steps = explain_hamming_general(bits, m)
        return DecodeResponse(
            decoded="".join(map(str, corrected)),
            success=info["error_pos"] != "uncorrectable",
            steps=[StepDTO(type=s.type, title=s.title, payload=s.payload)
                   for s in steps],
            error_positions=[info["error_pos"]] if info["error_pos"] not in (None, "uncorrectable") else []
        )