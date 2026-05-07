from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import hamming

app = FastAPI(
    title="Coding Playground API",
    description="API для кодирования и декодирования данных",
    version="0.1.0"
)

# CORS (пока разрешаем все origins для разработки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hamming.router)

@app.get("/")
def root():
    return {"message": "Coding API is running. Visit /docs for Swagger"}