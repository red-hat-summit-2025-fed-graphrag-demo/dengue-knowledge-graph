# Dengue Knowledge Graph API Service

This microservice provides a RESTful API for accessing and querying the Neo4j-based Dengue Knowledge Graph.

## Overview

The API exposes endpoints for:
- Querying the knowledge graph with Cypher
- Retrieving Dengue-specific data (symptoms, treatments, diagnostics, etc.)
- Accessing ontology relationships and concepts
- Graph operations (nodes, relationships)

## Development

### Prerequisites

- Python 3.11
- Neo4j database (the Neo4j service in this repository)

### Local Development

1. Create a Python virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_AUTH=none  # For local development without auth
```

3. Run the API server:

```bash
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. Access the API documentation at: http://localhost:8000/docs

### Container Development

Following project standards, the API can be run in a Podman container using the Red Hat UBI base image:

```bash
# Build the container
podman build -t dengue-api:local -f Containerfile .

# Run the container
podman run -d --name api-service \
  -p 8000:8000 \
  -e NEO4J_URI=bolt://neo4j-host:7687 \
  -e NEO4J_AUTH=none \
  dengue-api:local
```

## API Endpoints

The API provides the following endpoints:

### General

- `GET /` - Service information
- `GET /health` - Health check

### Graph Operations

- `POST /graph/query` - Run custom Cypher queries
- `GET /graph/nodes/{label}` - Get nodes by label
- `GET /graph/relationships/{type}` - Get relationships by type

### Dengue Specific Data

- `GET /dengue/symptoms` - Get Dengue symptoms
- `GET /dengue/classifications` - Get Dengue classifications
- `GET /dengue/diagnostics` - Get diagnostic tests
- `GET /dengue/treatments` - Get treatment protocols
- `GET /dengue/prevention` - Get prevention measures
- `GET /dengue/regions` - Get geographical regions with Dengue

### Ontology

- `GET /ontology/terms/{concept}` - Get ontology terms for a concept
- `GET /ontology/connected/{node_type}` - Get nodes connected to ontology terms

## Deployment

This service is deployed as part of the Dengue Knowledge Graph project using ArgoCD. The deployment configuration can be found in the `deployment/services/api` directory.
