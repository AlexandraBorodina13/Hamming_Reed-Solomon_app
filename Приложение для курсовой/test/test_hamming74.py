import numpy as np
from app.core.hamming import encode, decode

def test_single_error_correction():
    for msg_int in range(16):
        m = np.array([(msg_int>>i)&1 for i in [3,2,1,0]], dtype=int)
        code = encode(m)
        for pos in range(7):
            r = code.copy(); r[pos] ^= 1
            corr, info = decode(r)
            assert (corr == code).all()
