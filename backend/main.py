from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

app = FastAPI(
    title="Plantorix Backend API",
    description="AI-Powered Podiatric Pressure Mapping Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PatientInput(BaseModel):
    weight_kg: float
    foot_length_cm: float
    neuropathy_risk: int

@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to the Plantorix Backend API!"}

@app.post("/predict-pressure")
def predict_pressure(data: PatientInput):
    try:
        base_pressure = data.weight_kg * 2.5
        risk_multiplier = 1.0 + (data.neuropathy_risk * 0.15)
        
        pressure_grid = [
            [round(base_pressure * 0.8, 2), round(base_pressure * 0.7, 2)],
            [round(base_pressure * 0.9, 2), round(base_pressure * 1.1 * risk_multiplier, 2)]
        ]
        
        peak_pressure = max(max(row) for row in pressure_grid)
        status = "High Risk - Offloading Recommended" if peak_pressure > 180 else "Normal Range"

        return {
            "success": True,
            "peak_pressure_kpa": peak_pressure,
            "clinical_status": status,
            "pressure_matrix": pressure_grid,
            "recommended_offloading_depth_mm": -4.2 if peak_pressure > 180 else 0.0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))