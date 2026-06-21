from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict
import json
import statistics
from pathlib import Path

app = FastAPI()

# -------------------------
# CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# -------------------------
# Load telemetry JSON
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "q-vercel-latency.json"

try:
    with open(DATA_FILE, "r") as f:
        telemetry = json.load(f)
except Exception as e:
    telemetry = []
    print(f"Failed to load telemetry: {e}")

# -------------------------
# Models
# -------------------------
class RequestBody(BaseModel):
    regions: List[str]
    threshold_ms: float


class RegionMetrics(BaseModel):
    avg_latency: float
    p95_latency: float
    avg_uptime: float
    breaches: int


# -------------------------
# Root endpoint
# -------------------------
@app.get("/")
async def root():
    return {"message": "Latency API is running"}

# -------------------------
# OPTIONS (preflight)
# -------------------------
@app.options("/api/latency")
async def options_latency():
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )

# -------------------------
# POST endpoint
# -------------------------
@app.post("/api/latency", response_model=Dict[str, RegionMetrics])
async def latency_metrics(body: RequestBody):

    if not telemetry:
        raise HTTPException(status_code=500, detail="Telemetry data not loaded")

    result = {}

    for region in body.regions:

        records = [r for r in telemetry if r["region"] == region]

        if not records:
            continue

        latencies = [r["latency_ms"] for r in records]
        uptimes = [r["uptime_pct"] for r in records]

        latencies.sort()

        # Proper p95
        if len(latencies) == 1:
            p95 = latencies[0]
        else:
            index = int(0.95 * (len(latencies) - 1))
            p95 = latencies[index]

        result[region] = {
            "avg_latency": round(statistics.mean(latencies), 2),
            "p95_latency": round(p95, 2),
            "avg_uptime": round(statistics.mean(uptimes), 2),
            "breaches": sum(
                1 for value in latencies
                if value > body.threshold_ms
            ),
        }

    return JSONResponse(
        content=result,
        headers={
            "Access-Control-Allow-Origin": "*"
        },
    )