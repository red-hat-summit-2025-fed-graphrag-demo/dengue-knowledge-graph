# Dengue Knowledge Graph Scripts

This directory contains Python scripts for building, querying, and validating the Dengue Knowledge Graph. These scripts are used in the Elyra pipelines for data processing and are executed in sequence to build up the complete knowledge graph.

## Script Overview

### Core Graph Building Scripts
- `load-schema.py` - Creates the initial graph schema, constraints, and indexes
- `connect-dengue-symptoms.py` - Links symptoms to dengue classifications
- `connect-diagnostic-tests.py` - Links diagnostic tests to diseases
- `connect-non-clinical-entities.py` - Links regions and risk factors
- `connect-nodes-to-ontology.py` - Links nodes to ontology terms
- `add-references.py` - Adds citation references to nodes

### Validation Scripts
- `verify-graph.py` - Validates node and relationship counts
- `verify-ontology.py` - Validates ontology connections

### Utility Scripts
- `query_with_references.py` - Example queries with reference information
- `run-advanced-queries.py` - Advanced graph queries

## Development

These scripts are designed to be run either:
1. Directly with Python 3.11 using a virtual environment
2. As part of an Elyra pipeline workflow
3. Within containers managed by Tekton pipelines on OpenShift

## Environment Variables

All scripts respect the following environment variables:
- `NEO4J_URI` - Neo4j connection URI (default: "bolt://localhost:7687")
- `NEO4J_USER` - Neo4j username (default: "neo4j")
- `NEO4J_PASSWORD` - Neo4j password
- `NEO4J_AUTH` - Authentication type (set to "none" to disable authentication)
