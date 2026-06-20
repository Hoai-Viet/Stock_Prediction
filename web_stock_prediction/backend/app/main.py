import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import dashboard, predictions, news, data_explorer, model_metrics, signals, registration

app = FastAPI(title="Stock Predictor API", version="1.0.0")

default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://172.30.2.56:3000",
]
configured_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins or default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(data_explorer.router, prefix="/api/data-explorer", tags=["Data Explorer"])
app.include_router(model_metrics.router, prefix="/api/model-metrics", tags=["Model Metrics"])
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(registration.router, prefix="/api/registration", tags=["Registration"])


@app.get("/health")
def health():
    return {"status": "ok"}
