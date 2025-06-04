"""
Dengue Knowledge Graph Predictive Model Service
Provides ML-powered predictions for dengue outbreaks and risk assessment
"""
import os
import logging
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dengue Knowledge Graph Predictive Model",
    description="ML models for dengue outbreak prediction and risk assessment",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Environment Configuration ---
MODEL_PATH = os.environ.get("MODEL_PATH", "./models")
KG_API_URL = os.environ.get("KNOWLEDGE_GRAPH_API", "http://localhost:8000")

# --- Model Loading ---
def load_model(model_name):
    """Load ML model from disk"""
    model_file = os.path.join(MODEL_PATH, f"{model_name}.joblib")
    try:
        model = joblib.load(model_file)
        logger.info(f"Successfully loaded model: {model_name}")
        return model
    except Exception as e:
        logger.error(f"Error loading model {model_name}: {e}")
        return None

# Dictionary to store loaded models
models = {}

# Models to load at startup
MODEL_NAMES = ["dengue_risk_classifier", "outbreak_predictor"]

@app.on_event("startup")
async def startup_event():
    """Load models at startup"""
    for model_name in MODEL_NAMES:
        models[model_name] = load_model(model_name)
    
    # If models aren't available yet, create placeholders
    if not all(models.values()):
        logger.warning("Some models not found. Using placeholder predictions for now.")


# --- API Models ---
class PredictionFeatures(BaseModel):
    """Features for making predictions"""
    temperature: float = Field(..., description="Average temperature in Celsius")
    humidity: float = Field(..., description="Relative humidity percentage")
    rainfall: float = Field(..., description="Rainfall in mm")
    population_density: float = Field(..., description="Population density per km²")
    previous_cases: int = Field(..., description="Number of cases in previous period")
    season: str = Field(..., description="Season (dry, rainy)")
    region: Optional[str] = Field(None, description="Region identifier")


class RiskPrediction(BaseModel):
    """Risk prediction response"""
    risk_level: str = Field(..., description="Predicted risk level")
    risk_score: float = Field(..., description="Numerical risk score")
    confidence: float = Field(..., description="Prediction confidence")
    factors: Dict[str, float] = Field(..., description="Contributing factors")
    recommendations: List[str] = Field(..., description="Recommended actions")


class OutbreakPrediction(BaseModel):
    """Outbreak prediction response"""
    probability: float = Field(..., description="Probability of outbreak")
    threshold_exceeded: bool = Field(..., description="Whether outbreak threshold is exceeded")
    predicted_cases: Optional[int] = Field(None, description="Predicted number of cases")
    timeframe: str = Field(..., description="Prediction timeframe")
    model_version: str = Field(..., description="Model version used")


# --- API Routes ---
@app.get("/")
async def root():
    """Service root endpoint with information"""
    return {
        "service": "Dengue Knowledge Graph Predictive Model",
        "version": "1.0.0",
        "status": "active",
        "documentation": "/docs",
        "models_loaded": [name for name, model in models.items() if model is not None]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    models_status = {name: "loaded" if model is not None else "not_loaded" 
                    for name, model in models.items()}
    return {"status": "healthy", "models": models_status}


@app.post("/predict/risk", response_model=RiskPrediction)
async def predict_risk(features: PredictionFeatures):
    """Predict dengue risk level based on environmental and demographic factors"""
    try:
        if "dengue_risk_classifier" not in models or models["dengue_risk_classifier"] is None:
            # Return placeholder prediction for now
            return _placeholder_risk_prediction(features)
        
        # Convert input to format expected by model
        features_df = pd.DataFrame([features.dict()])
        
        # Perform any needed feature transformations
        # (In a real implementation, this would include proper preprocessing)
        
        # Get prediction
        model = models["dengue_risk_classifier"]
        risk_score = float(model.predict_proba(features_df)[0][1])
        
        # Map score to risk level
        risk_level = "Low"
        if risk_score > 0.7:
            risk_level = "High"
        elif risk_score > 0.4:
            risk_level = "Medium"
            
        # Get feature importances (if possible)
        factors = {}
        if hasattr(model, 'feature_importances_'):
            feature_names = features_df.columns
            importances = model.feature_importances_
            for name, importance in zip(feature_names, importances):
                factors[name] = float(importance)
        
        # Generate recommendations based on risk level
        recommendations = _generate_recommendations(risk_level, features)
        
        return RiskPrediction(
            risk_level=risk_level,
            risk_score=risk_score,
            confidence=0.85,  # Placeholder confidence
            factors=factors,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Error predicting risk: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.post("/predict/outbreak", response_model=OutbreakPrediction)
async def predict_outbreak(features: PredictionFeatures):
    """Predict probability of dengue outbreak in the next 30 days"""
    try:
        if "outbreak_predictor" not in models or models["outbreak_predictor"] is None:
            # Return placeholder prediction for now
            return _placeholder_outbreak_prediction(features)
        
        # Convert input to format expected by model
        features_df = pd.DataFrame([features.dict()])
        
        # Perform any needed feature transformations
        # (In a real implementation, this would include proper preprocessing)
        
        # Get prediction
        model = models["outbreak_predictor"]
        outbreak_prob = float(model.predict_proba(features_df)[0][1])
        
        # Predict cases if available
        predicted_cases = None
        if hasattr(model, 'predict_cases'):
            predicted_cases = int(model.predict_cases(features_df)[0])
        
        return OutbreakPrediction(
            probability=outbreak_prob,
            threshold_exceeded=outbreak_prob > 0.6,
            predicted_cases=predicted_cases,
            timeframe="30 days",
            model_version="1.0.0"
        )
        
    except Exception as e:
        logger.error(f"Error predicting outbreak: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/models")
async def list_models():
    """List available prediction models"""
    return {
        "available_models": [
            {
                "name": "dengue_risk_classifier",
                "description": "Classifies dengue risk levels based on environmental factors",
                "status": "loaded" if models.get("dengue_risk_classifier") is not None else "not_loaded",
                "version": "1.0.0"
            },
            {
                "name": "outbreak_predictor",
                "description": "Predicts probability of dengue outbreak in next 30 days",
                "status": "loaded" if models.get("outbreak_predictor") is not None else "not_loaded",
                "version": "1.0.0"
            }
        ]
    }


# --- Helper Functions ---
def _placeholder_risk_prediction(features: PredictionFeatures) -> RiskPrediction:
    """Generate placeholder risk prediction based on heuristics"""
    # Simple heuristic based on temperature, rainfall and previous cases
    risk_score = 0.0
    
    # Temperature factor (higher temps = higher risk)
    if features.temperature > 30:
        risk_score += 0.3
    elif features.temperature > 25:
        risk_score += 0.2
    
    # Rainfall factor
    if features.rainfall > 200:
        risk_score += 0.3
    elif features.rainfall > 100:
        risk_score += 0.2
    
    # Previous cases factor
    if features.previous_cases > 50:
        risk_score += 0.4
    elif features.previous_cases > 10:
        risk_score += 0.2
    
    # Season factor
    if features.season.lower() == "rainy":
        risk_score += 0.2
    
    # Cap at 1.0
    risk_score = min(risk_score, 1.0)
    
    # Map score to risk level
    risk_level = "Low"
    if risk_score > 0.7:
        risk_level = "High"
    elif risk_score > 0.4:
        risk_level = "Medium"
    
    # Generate factors dict
    factors = {
        "temperature": 0.3 if features.temperature > 25 else 0.1,
        "rainfall": 0.3 if features.rainfall > 100 else 0.1,
        "previous_cases": 0.3 if features.previous_cases > 10 else 0.1,
        "season": 0.2 if features.season.lower() == "rainy" else 0.1,
        "population_density": 0.2 if features.population_density > 1000 else 0.1
    }
    
    # Generate recommendations
    recommendations = _generate_recommendations(risk_level, features)
    
    return RiskPrediction(
        risk_level=risk_level,
        risk_score=risk_score,
        confidence=0.7,  # Lower confidence for placeholder
        factors=factors,
        recommendations=recommendations
    )


def _placeholder_outbreak_prediction(features: PredictionFeatures) -> OutbreakPrediction:
    """Generate placeholder outbreak prediction based on heuristics"""
    # Simple heuristic based on temperature, rainfall and previous cases
    outbreak_prob = 0.0
    
    # Temperature factor
    if features.temperature > 30:
        outbreak_prob += 0.3
    elif features.temperature > 25:
        outbreak_prob += 0.2
    
    # Rainfall factor
    if features.rainfall > 200:
        outbreak_prob += 0.3
    elif features.rainfall > 100:
        outbreak_prob += 0.2
    
    # Previous cases factor (most important)
    if features.previous_cases > 50:
        outbreak_prob += 0.4
    elif features.previous_cases > 10:
        outbreak_prob += 0.2
    
    # Population density
    if features.population_density > 5000:
        outbreak_prob += 0.2
    elif features.population_density > 1000:
        outbreak_prob += 0.1
    
    # Cap at 1.0
    outbreak_prob = min(outbreak_prob, 1.0)
    
    # Estimate cases based on previous and probability
    predicted_cases = int(features.previous_cases * (1 + outbreak_prob))
    
    return OutbreakPrediction(
        probability=outbreak_prob,
        threshold_exceeded=outbreak_prob > 0.6,
        predicted_cases=predicted_cases,
        timeframe="30 days",
        model_version="placeholder"
    )


def _generate_recommendations(risk_level: str, features: PredictionFeatures) -> List[str]:
    """Generate recommendations based on risk level and features"""
    recommendations = []
    
    if risk_level == "High":
        recommendations = [
            "Implement immediate vector control measures",
            "Ensure adequate medical supplies for treatment",
            "Activate community awareness campaigns",
            "Increase surveillance for early case detection",
            "Deploy mobile medical teams to high-risk areas"
        ]
    elif risk_level == "Medium":
        recommendations = [
            "Enhance routine vector surveillance",
            "Prepare medical facilities for potential cases",
            "Conduct targeted community education",
            "Clear standing water sources",
            "Monitor weather patterns for increased rainfall"
        ]
    else:  # Low
        recommendations = [
            "Maintain routine surveillance",
            "Continue public education on prevention",
            "Ensure drainage systems are functioning",
            "Update emergency response plans",
            "Monitor regional case reports"
        ]
    
    # Add specific recommendations based on features
    if features.rainfall > 150:
        recommendations.append("Address standing water accumulation after heavy rainfall")
    
    if features.temperature > 30:
        recommendations.append("Advise community on heat protection measures that also prevent mosquito exposure")
    
    if features.previous_cases > 0:
        recommendations.append("Focus prevention efforts in areas with previous cases")
    
    return recommendations


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
