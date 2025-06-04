# Dengue Knowledge Graph - Developer Guide

This guide provides comprehensive information for developers working on the Dengue Knowledge Graph project, following the established Red Hat Summit 2025 standards.

## Project Overview

The Dengue Knowledge Graph project provides a comprehensive microservices-based architecture for managing, analyzing, and visualizing dengue fever data. The system consists of multiple interconnected services that work together to deliver knowledge graph capabilities and AI-powered insights.

## Architecture

The system follows a microservices architecture with the following components:

1. **Neo4j Service**: Core knowledge graph database containing dengue fever data, relationships, and ontologies.
2. **API Service**: FastAPI-based REST API for accessing the knowledge graph data.
3. **Frontend**: React-based web interface for visualizing and interacting with the knowledge graph.
4. **Agent Workflow**: LLM-powered agentic workflows for guided exploration of dengue knowledge.
5. **Predictive Model**: ML models for dengue outbreak prediction and risk assessment.
6. **Table RAG**: Service for analyzing structured tabular data with Retrieval Augmented Generation.

![Architecture Diagram](architecture.png)

## Development Standards

All development must adhere to the following standards:

### Programming Languages

- **Python**: Version 3.11 for all Python services
- **JavaScript/TypeScript**: Node.js 18 for frontend development

### Containerization

- **Container Format**: Containerfile (OCI-compliant)
- **Base Images**: Red Hat Universal Base Image (UBI)
- **Container Runtime**: Podman for local development and testing
- **Target Environment**: OpenShift Container Platform

### Dependency Management

1. **Initial Selection**:
   - Use tools like pipreqs (Python) or npm install (Node.js) to discover latest compatible versions
   - Avoid hardcoding specific package versions based solely on LLM training data

2. **Version Locking**:
   - Lock package versions in requirements.txt, package-lock.json, etc.
   - For Python: Use pip-compile or Poetry to generate deterministic lockfiles
   - For containers: Specify exact versions in Containerfiles

3. **Version Updates**:
   - Update versions deliberately after proper testing, not automatically
   - Schedule regular dependency reviews to address security patches

4. **Documentation**:
   - Document dependency update strategy in the project README
   - Include instructions for properly updating dependencies

### Local Development

- Use Python virtual environments (venv) for Python development
- Use Podman for container-based testing
- Always test applications in a container before deployment

## Project Structure

```
/dengue-knowledge-graph/
├── README.md                    # Project overview
├── .gitignore                   # Git ignore patterns
├── docs/                        # Documentation
├── services/                    # Individual microservices
│   ├── neo4j/                   # Neo4j knowledge graph service
│   ├── api/                     # FastAPI service
│   ├── frontend/                # React-based frontend
│   ├── agent-workflow/          # LLM agent service
│   ├── predictive-model/        # ML prediction service
│   └── table-rag/               # Table data analysis service
├── scripts/                     # Shared scripts
├── pipelines/                   # Pipeline definitions
│   ├── elyra/                   # Elyra pipeline definitions
│   └── local/                   # Local pipeline testing
├── data/                        # Sample/test data
└── deployment/                  # Kubernetes/OpenShift resources
    ├── bootstrap/               # ArgoCD bootstrap configurations
    └── services/                # Service-specific deployments
```

## Development Workflow

### Setting Up Your Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/example/dengue-knowledge-graph.git
   cd dengue-knowledge-graph
   ```

2. **Run the local development setup script**:
   ```bash
   ./scripts/local-dev-setup.sh
   ```
   This script will:
   - Create Python virtual environments for each service
   - Install dependencies
   - Build and start containers for local development
   - Load sample data into the knowledge graph

3. **Access local services**:
   - Neo4j Browser: http://localhost:7474
   - API Documentation: http://localhost:8000/docs
   - Frontend: http://localhost:3000
   - Agent Workflow: http://localhost:8001/docs
   - Predictive Model: http://localhost:8002/docs
   - Table RAG: http://localhost:8003/docs

### Service Development

Each service follows specific development practices:

#### Neo4j Service

This service manages the knowledge graph schema, constraints, and core data:

```bash
cd services/neo4j
# Activate the virtual environment
source .venv/bin/activate
# Run schema loading scripts
python scripts/load-schema.py
```

#### API Service

The API service provides a REST interface to the knowledge graph:

```bash
cd services/api
# Activate the virtual environment
source .venv/bin/activate
# Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Service

The React-based frontend for visualizing the knowledge graph:

```bash
cd services/frontend
# Install dependencies
npm install
# Run the development server
npm start
```

#### Agent Workflow, Predictive Model, and Table RAG Services

These services follow similar patterns to the API service, each with their own virtual environments and development servers.

### Building and Testing Containers

Always use Podman with Red Hat UBI base images for containers:

```bash
cd services/[service-name]
# Build the container
podman build -t dengue-[service-name]:local -f Containerfile .
# Run the container
podman run -d --name [service-name] -p [port]:[port] dengue-[service-name]:local
```

## Knowledge Graph Pipeline

The Dengue Knowledge Graph is built by a series of scripts that:

1. Create the initial schema and constraints
2. Load ontology data
3. Connect symptoms to dengue classifications
4. Connect diagnostic tests to diseases
5. Link non-clinical entities
6. Add citations and references

To run the pipeline locally:

```bash
cd pipelines/local
./test_pipeline.sh
```

## Deployment

The project is designed for deployment on OpenShift using ArgoCD:

1. **Set up ArgoCD**:
   ```bash
   oc apply -f deployment/bootstrap/applicationset.yaml
   ```

2. **Monitor deployment**:
   ```bash
   oc get applications -n openshift-gitops
   ```

3. **Access services**:
   ```bash
   oc get routes
   ```

## Troubleshooting

Common issues and their solutions:

1. **Neo4j Connection Issues**:
   - Check that Neo4j container is running: `podman ps | grep neo4j`
   - Verify port bindings: `podman port neo4j-dengue`
   - Check logs: `podman logs neo4j-dengue`

2. **API Service Issues**:
   - Verify connection to Neo4j: Check `NEO4J_URI` environment variable
   - Review API logs: `podman logs dengue-api`

3. **Container Build Failures**:
   - Ensure you're using Python 3.11
   - Verify that all required dependencies are in requirements.txt
   - Check for syntax errors in the Containerfile

## Additional Resources

- [Neo4j Cypher Documentation](https://neo4j.com/docs/cypher-manual/current/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/docs/getting-started.html)
- [OpenShift Documentation](https://docs.openshift.com/)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
