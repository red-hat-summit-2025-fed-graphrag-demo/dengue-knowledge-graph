# Local Pipeline Testing

This directory contains scripts and configurations for testing the Dengue Knowledge Graph pipeline locally using Podman, following the project's containerization standards.

## Overview

The local testing setup allows you to:

1. Run the complete pipeline locally using Podman containers
2. Test individual pipeline components
3. Validate the Neo4j knowledge graph construction
4. Ensure compatibility with the eventual OpenShift deployment

## Usage

### Prerequisites

- Podman installed (as per project standards)
- Python 3.11 with virtual environment for local development

### Testing the Pipeline

```bash
# Create a Python virtual environment (for script development)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the complete pipeline test
./test_pipeline.sh

# Test individual components
./test_pipeline.sh --component schema
./test_pipeline.sh --component symptoms
```

## Pipeline Validation

After running the pipeline locally, you can validate the graph structure by:

1. Connecting to Neo4j Browser at http://localhost:7475
2. Running the validation queries in `/scripts/verify-graph.py`

## Container Testing

As per project standards, all containers are built using Red Hat UBI base images and tested with Podman before OpenShift deployment:

```bash
# Build and test the Neo4j container
cd ../../services/neo4j
podman build -t neo4j-dengue:local -f Containerfile .
podman run -d --name neo4j-test -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=none neo4j-dengue:local
```
