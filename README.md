# Dengue Knowledge Graph

A comprehensive system for exploring, analyzing, and visualizing dengue fever data through a knowledge graph, supported by ML models and intelligent agent workflows.

## Overview

This project provides a microservices-based architecture for managing dengue fever knowledge, offering:

- Neo4j-based knowledge graph for medical knowledge representation
- FastAPI backend service for graph data access
- ML-powered prediction models for dengue outbreak risk assessment
- Interactive agent workflows for guided exploration of dengue data
- Table RAG (Retrieval Augmented Generation) for structured data insights
- Web-based UI for interactive visualization and exploration

## Architecture

The system consists of multiple microservices deployed using ArgoCD:

- **Neo4j Service**: Knowledge graph database containing dengue fever data
- **API Service**: FastAPI-based backend for accessing graph data
- **Frontend**: Web-based UI for interacting with the knowledge graph
- **Agent Workflow**: LLM-powered agentic workflow for guided exploration
- **Predictive Model**: ML models for dengue outbreak prediction
- **Table RAG**: Service for analyzing structured data with LLMs

## Development

Each service is containerized using Red Hat UBI base images and can be developed independently. The repository follows a modular structure with clear separation of concerns:

- `services/`: Individual containerized applications
- `scripts/`: Shared processing scripts
- `pipelines/`: Pipeline definitions for data processing
- `deployment/`: Kubernetes/OpenShift resources for ArgoCD

## Deployment

The system is designed to be deployed on OpenShift with ArgoCD. See `docs/deployment.md` for detailed deployment instructions.
