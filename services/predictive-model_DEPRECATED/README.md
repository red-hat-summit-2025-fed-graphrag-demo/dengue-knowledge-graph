# Dengue Knowledge Graph Predictive Model

This microservice provides ML-based predictions for dengue outbreaks and risk assessment as part of the Dengue Knowledge Graph project.

## Overview

The Predictive Model service uses machine learning models to:
- Predict dengue outbreak risk based on environmental and demographic factors
- Forecast potential case numbers in different regions
- Identify key risk factors contributing to dengue transmission
- Generate preventive action recommendations based on risk profiles

## Development

### Prerequisites

- Python 3.11 (as per project standards)
- Neo4j database (the Neo4j service in this repository)
- ML model files (stored in the `models/` directory)

### Local Development

1. Create a Python virtual environment (as per project development standards):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_AUTH=none  # For local development without auth
export KNOWLEDGE_GRAPH_API=http://localhost:8000
export MODEL_PATH=./models
```

3. Create the models directory and add placeholder models if needed:

```bash
mkdir -p models
# During development, models will be trained and saved here
```

4. Run the API server:

```bash
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

5. Access the API documentation at: http://localhost:8080/docs

### Container Development

Following project standards, the service can be run in a Podman container using the Red Hat UBI base image:

```bash
# Build the container
podman build -t dengue-predictive-model:local -f Containerfile .

# Run the container
podman run -d --name predictive-model-service \
  -p 8080:8080 \
  -e NEO4J_URI=bolt://neo4j-host:7687 \
  -e NEO4J_AUTH=none \
  -e KNOWLEDGE_GRAPH_API=http://api-host:8000 \
  -e MODEL_PATH=/app/models \
  dengue-predictive-model:local
```

## API Endpoints

The service provides the following endpoints:

- `GET /` - Service information and loaded models
- `GET /health` - Health check and model status
- `POST /predict/risk` - Predict dengue risk level based on environmental factors
- `POST /predict/outbreak` - Predict probability of dengue outbreak
- `GET /models` - List available prediction models

## Model Development

The service is designed to load trained ML models from the `models/` directory. During development:

1. Train models in notebooks or separate scripts 
2. Save trained models using joblib:
   ```python
   import joblib
   joblib.dump(model, "models/dengue_risk_classifier.joblib")
   ```
3. The service will automatically load these models at startup

## Deployment

This service is deployed as part of the Dengue Knowledge Graph project using ArgoCD. The deployment configuration can be found in the `deployment/services/predictive-model` directory.
