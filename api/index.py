from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import statistics
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "q-vercel-latency.json", "r") as f:
    telemetry = json.load(f)


class RequestBody(BaseModel):
    regions: List[str]
    threshold_ms: float


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/api/latency")
async def latency_metrics(body: RequestBody):
    response = {"regions": []}

    for region in body.regions:
        records = [r for r in telemetry if r["region"] == region]

        if not records:
            continue

        latencies = sorted([r["latency_ms"] for r in records])
        uptimes = [r["uptime_pct"] for r in records]

        avg_latency = statistics.mean(latencies)

        if len(latencies) == 1:
            p95 = latencies[0]
        else:
            p95 = statistics.quantiles(
                latencies,
                n=100,
                method="inclusive"
            )[94]

        avg_uptime = statistics.mean(uptimes)

        breaches = sum(
            1
            for latency in latencies
            if latency > body.threshold_ms
        )

        response["regions"].append(
            {
                "region": region,
                "avg_latency": round(avg_latency, 2),
                "p95_latency": round(p95, 2),
                "avg_uptime": round(avg_uptime, 2),
                "breaches": breaches,
            }
        )

    return response