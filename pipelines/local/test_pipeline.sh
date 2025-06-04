#!/bin/bash
#
# Dengue Knowledge Graph Pipeline Test Script
# Runs all microservices in containers using Podman
# Following Red Hat Summit 2025 project standards
#

set -e  # Exit on error

# Configuration
TEST_NEO4J_PORT=7475
TEST_NEO4J_BOLT_PORT=7688
TEST_API_PORT=8001
FRONTEND_PORT=3000
NEO4J_PASSWORD="neo4j"
LOG_DIR="pipeline_test_logs"
CURRENT_DIR=$(pwd)
PROJECT_ROOT=$(realpath "${CURRENT_DIR}/../..")
NEO4J_DATA_DIR="${CURRENT_DIR}/neo4j-test-data"

# Print section header
section() {
    echo -e "\n\033[1;36m==== $1 ====\033[0m\n"
}

# Print step info
step() {
    echo -e "\033[1;33m--> $1\033[0m"
}

# Print success message
success() {
    echo -e "\033[1;32m✓ $1\033[0m"
}

# Print error message and exit
error() {
    echo -e "\033[1;31m✗ ERROR: $1\033[0m"
    exit 1
}

# Check for Podman (required per project standards)
if ! command -v podman &> /dev/null; then
    error "Podman is not installed. Please install Podman first (required per project standards)."
fi

# Create log directory
mkdir -p "$LOG_DIR"

section "CLEANUP (PRE-TEST)"
step "Removing any existing test containers and networks..."

# Force cleanup of any existing containers
podman stop neo4j-test api-test frontend-test 2>/dev/null || true
podman rm -f neo4j-test api-test frontend-test 2>/dev/null || true
podman network rm -f dengue-test-network 2>/dev/null || true

# Remove temp data directory
step "Preparing Neo4j data directory..."
rm -rf "${NEO4J_DATA_DIR}" &> /dev/null || true
mkdir -p "${NEO4J_DATA_DIR}"
chmod 777 "${NEO4J_DATA_DIR}"  # Ensure container has full access
success "Data directory prepared"

success "Cleanup completed"

section "SETUP TEST ENVIRONMENT"
step "Creating test network..."
podman network create dengue-test-network || error "Failed to create network"
success "Test network created"

step "Starting Neo4j test container..."
echo "Building neo4j-test container from Containerfile..."
podman build -t neo4j-test-image -f "${PROJECT_ROOT}/services/neo4j/Containerfile" "${PROJECT_ROOT}/services/neo4j" || error "Failed to build Neo4j container"

# Run the container with auth disabled for testing
podman run -d --name neo4j-test \
  --network dengue-test-network \
  -p ${TEST_NEO4J_PORT}:7474 -p ${TEST_NEO4J_BOLT_PORT}:7687 \
  -e NEO4J_AUTH=none \
  -v "${NEO4J_DATA_DIR}:/data:Z" \
  neo4j-test-image || error "Failed to start Neo4j container"

# Wait for Neo4j to start
step "Waiting for Neo4j to start (this may take a minute)..."
sleep 20  # Give Neo4j time to initialize
success "Neo4j test container started"

section "PIPELINE EXECUTION"

step "1. Loading Schema and Base Nodes..."
podman run --rm --network dengue-test-network \
  -v "${PROJECT_ROOT}/scripts:/app/scripts:Z" \
  -e NEO4J_URI=bolt://neo4j-test:7687 \
  -e NEO4J_AUTH=none \
  registry.access.redhat.com/ubi8/python-311:latest \
  bash -c "cd /app && pip install neo4j owlready2 && python scripts/load-schema.py" || error "Schema loading failed"
success "Schema loaded successfully"

step "2. Connecting Symptoms to Dengue Classifications..."
podman run --rm --network dengue-test-network \
  -v "${PROJECT_ROOT}/scripts:/app/scripts:Z" \
  -e NEO4J_URI=bolt://neo4j-test:7687 \
  -e NEO4J_AUTH=none \
  registry.access.redhat.com/ubi8/python-311:latest \
  bash -c "cd /app && pip install neo4j && python scripts/connect-dengue-symptoms.py" || error "Symptom connections failed"
success "Symptoms connected successfully"

step "3. Connecting Diagnostic Tests to Diseases..."
podman run --rm --network dengue-test-network \
  -v "${PROJECT_ROOT}/scripts:/app/scripts:Z" \
  -e NEO4J_URI=bolt://neo4j-test:7687 \
  -e NEO4J_AUTH=none \
  registry.access.redhat.com/ubi8/python-311:latest \
  bash -c "cd /app && pip install neo4j && python scripts/connect-diagnostic-tests.py" || error "Diagnostic test connections failed"
success "Diagnostic tests connected successfully"

step "4. Connecting Non-Clinical Entities..."
podman run --rm --network dengue-test-network \
  -v "${PROJECT_ROOT}/scripts:/app/scripts:Z" \
  -e NEO4J_URI=bolt://neo4j-test:7687 \
  -e NEO4J_AUTH=none \
  registry.access.redhat.com/ubi8/python-311:latest \
  bash -c "cd /app && pip install neo4j && python scripts/connect-non-clinical-entities.py" || error "Non-clinical connections failed"
success "Non-clinical entities connected successfully"

step "5. Connecting Ontology Terms..."
podman run --rm --network dengue-test-network \
  -v "${PROJECT_ROOT}/scripts:/app/scripts:Z" \
  -e NEO4J_URI=bolt://neo4j-test:7687 \
  -e NEO4J_AUTH=none \
  registry.access.redhat.com/ubi8/python-311:latest \
  bash -c "cd /app && pip install neo4j owlready2 && python scripts/connect-nodes-to-ontology.py" || error "Ontology connections failed"
success "Ontology terms connected successfully"

step "6. Adding Citations and References..."
podman run --rm --network dengue-test-network \
  -v "${PROJECT_ROOT}/scripts:/app/scripts:Z" \
  -e NEO4J_URI=bolt://neo4j-test:7687 \
  -e NEO4J_AUTH=none \
  registry.access.redhat.com/ubi8/python-311:latest \
  bash -c "cd /app && pip install neo4j && python scripts/add-references.py" || error "Adding references failed"
success "References added successfully"

# Add FastAPI service deployment when ready
# step "Starting FastAPI test container..."

section "TEST ENVIRONMENT INFO"

cat << EOF

The test environment is now running. You can access:

1. Neo4j Browser: http://localhost:${TEST_NEO4J_PORT}
   - No authentication required (NEO4J_AUTH=none)

To stop the test environment:
  podman stop neo4j-test
  podman rm neo4j-test
  podman network rm dengue-test-network

EOF
