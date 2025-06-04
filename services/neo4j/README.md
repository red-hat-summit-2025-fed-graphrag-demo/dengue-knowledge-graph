# Neo4j Knowledge Graph Service

This service provides the Neo4j graph database for the Dengue Knowledge Graph project, built on Red Hat UBI base images as per project standards.

## Overview

The Neo4j service stores and manages the knowledge graph data related to dengue fever, including:

- Disease classifications and symptoms
- Diagnostic tests and procedures
- Geographic information and regional risk factors
- Temporal data on outbreaks
- Medical ontology mappings
- Citations and references

## Container Specifications

- **Base Image**: Red Hat UBI 9
- **Neo4j Version**: 5.21.0
- **Java Version**: 17
- **Exposed Ports**:
  - 7474: HTTP (Neo4j Browser)
  - 7687: Bolt (Driver protocol)

## Local Development

For local development, you can use Podman to build and run the container:

```bash
# Build the image
podman build -t neo4j-dengue:latest -f Containerfile .

# Run with authentication disabled (development only)
podman run -d --name neo4j-dengue \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=none \
  -v "$(pwd)/data:/data:Z" \
  neo4j-dengue:latest

# Run with authentication (more secure)
podman run -d --name neo4j-dengue \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/yoursecurepassword \
  -v "$(pwd)/data:/data:Z" \
  neo4j-dengue:latest
```

## OpenShift Deployment

For OpenShift deployment, this service is deployed using ArgoCD with the configuration in `deployment/services/neo4j/`. See the main project documentation for details on the full deployment process.

## Data Persistence

Data is stored in a persistent volume mounted at `/data` within the container. Make sure to configure appropriate persistent volumes in your OpenShift environment.

## Configuration

Configuration is managed through environment variables:

- `NEO4J_AUTH`: Authentication settings (e.g., `neo4j/password` or `none`)
- `NEO4J_dbms_memory_heap_max__size`: Maximum heap size
- `NEO4J_dbms_memory_pagecache_size`: Page cache size

Additional configuration can be provided via ConfigMaps mounted at `/var/lib/neo4j/conf`.
