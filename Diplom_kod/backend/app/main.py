from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import hamming, bch, reed_solomon, convolutional, comparison, channel

app = FastAPI(
    title="Coding Playground API",
    description="API для кодирования и декодирования данных",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки, позже ограничить
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hamming.router)
app.include_router(bch.router)
app.include_router(reed_solomon.router)
app.include_router(convolutional.router)
app.include_router(comparison.router)
app.include_router(channel.router)

@app.get("/")
def root():
    return {"message": "Coding API is running. Visit /docs for Swagger"}