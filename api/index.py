from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import statistics
import os

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load telemetry data from the bundled JSON file
with open("q-vercel-latency.json", "r") as f:
    telemetry = json.load(f)  # expect a list of records with keys: region, latency, uptime

class RequestBody(BaseModel):
    regions: List[str]
    threshold_ms: int

class RegionMetrics(BaseModel):
    avg_latency: float
    p95_latency: float
    avg_uptime: float
    breaches: int

@app.post("/api/latency", response_model=Dict[str, RegionMetrics])
async def latency_metrics(body: RequestBody):
    regions = set(body.regions)
    threshold = body.threshold_ms

    # Filter data for requested regions
    filtered = [r for r in telemetry if r.get("region") in regions]
    if not filtered:
        raise HTTPException(status_code=400, detail="No data for given regions")

    # Group by region
    grouped = {}
    for record in filtered:
        region = record["region"]
        grouped.setdefault(region, []).append(record)

    result = {}
    for region, records in grouped.items():
        latencies = [r["latency_ms"] for r in records]
        uptimes = [r["uptime_pct"] for r in records]
        if not latencies or not uptimes:
            continue

        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 20 else max(latencies)  # crude 95th
        avg_uptime = statistics.mean(uptimes)
        breaches = sum(1 for l in latencies if l > threshold)

        result[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }

    return result