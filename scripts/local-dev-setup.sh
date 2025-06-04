#!/bin/bash
#
# Dengue Knowledge Graph - Local Development Setup
# Sets up the local development environment for working with the Dengue Knowledge Graph
# Follows Red Hat Summit 2025 standards:
# - Python 3.11 for all Python development
# - Podman for container-based testing
# - Red Hat UBI base images for all containers
#

set -e  # Exit on error

# Configuration
LOG_DIR="local_dev_logs"
NEO4J_TEST_PORT=7474
NEO4J_BOLT_TEST_PORT=7687
API_TEST_PORT=8000
FRONTEND_TEST_PORT=3000
AGENT_WORKFLOW_TEST_PORT=8001
PREDICTIVE_MODEL_TEST_PORT=8002
TABLE_RAG_TEST_PORT=8003
ROOT_DIR=$(pwd)

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print section header
section() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

# Print step info
step() {
    echo -e "${YELLOW}--> $1${NC}"
}

# Print success message
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Print error message and exit
error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
    exit 1
}

# Check for Podman (required per project standards)
if ! command -v podman &> /dev/null; then
    error "Podman is not installed. Please install Podman first (required per project standards)."
fi

# Create log directory
mkdir -p "$LOG_DIR"

# Check if Python 3.11 is installed
if ! command -v python3.11 &> /dev/null; then
    echo -e "${YELLOW}Warning: Python 3.11 not found. Project standard is Python 3.11.${NC}"
    echo -e "${YELLOW}Please install Python 3.11 for development work.${NC}"
fi

section "SETTING UP LOCAL DEVELOPMENT ENVIRONMENT"

step "Creating Python virtual environments for development..."

# Create virtual environments for each service component
create_venv() {
    local service_name=$1
    local service_dir="services/$service_name"
    
    if [ -d "$service_dir" ]; then
        step "Setting up virtual environment for $service_name service"
        cd "$service_dir"
        
        # Create virtual environment if it doesn't exist
        if [ ! -d ".venv" ]; then
            python3.11 -m venv .venv
            success "Created virtual environment for $service_name"
        else
            echo "Virtual environment already exists for $service_name"
        fi
        
        # Install requirements if requirements.txt exists
        if [ -f "requirements.txt" ]; then
            step "Installing requirements for $service_name"
            source .venv/bin/activate
            pip install -r requirements.txt
            deactivate
            success "Installed dependencies for $service_name"
        fi
        
        cd "$ROOT_DIR"
    fi
}

# Create virtual environments for each service
create_venv "api"
create_venv "agent-workflow"
create_venv "predictive-model"
create_venv "table-rag"

success "Virtual environments set up successfully"

section "LOCAL CONTAINER SETUP"

step "Preparing for local container development..."

# Create a local dev network for the containers to communicate
podman network rm -f dengue-dev-network &> /dev/null || true
podman network create dengue-dev-network || error "Failed to create network"
success "Created container network: dengue-dev-network"

step "Building Neo4j container..."
cd "$ROOT_DIR/services/neo4j"
podman build -t neo4j-dengue:local -f Containerfile . || error "Failed to build Neo4j container"
success "Built Neo4j container"

step "Building API container..."
cd "$ROOT_DIR/services/api"
podman build -t dengue-api:local -f Containerfile . || error "Failed to build API container"
success "Built API container"

# Optionally build other service containers if they're ready
if [ -f "$ROOT_DIR/services/frontend/Containerfile" ]; then
    step "Building Frontend container..."
    cd "$ROOT_DIR/services/frontend"
    podman build -t dengue-frontend:local -f Containerfile . || echo "Note: Frontend build skipped or failed"
fi

if [ -f "$ROOT_DIR/services/agent-workflow/Containerfile" ]; then
    step "Building Agent Workflow container..."
    cd "$ROOT_DIR/services/agent-workflow"
    podman build -t dengue-agent-workflow:local -f Containerfile . || echo "Note: Agent Workflow build skipped or failed"
fi

if [ -f "$ROOT_DIR/services/predictive-model/Containerfile" ]; then
    step "Building Predictive Model container..."
    cd "$ROOT_DIR/services/predictive-model"
    podman build -t dengue-predictive-model:local -f Containerfile . || echo "Note: Predictive Model build skipped or failed"
fi

if [ -f "$ROOT_DIR/services/table-rag/Containerfile" ]; then
    step "Building Table RAG container..."
    cd "$ROOT_DIR/services/table-rag"
    podman build -t dengue-table-rag:local -f Containerfile . || echo "Note: Table RAG build skipped or failed"
fi

cd "$ROOT_DIR"

section "STARTING SERVICES"

step "Starting Neo4j container..."
# Use custom credentials instead of default neo4j/neo4j to avoid password change requirement
podman run -d --name neo4j-dengue \
  --network dengue-dev-network \
  -p ${NEO4J_TEST_PORT}:7474 -p ${NEO4J_BOLT_TEST_PORT}:7687 \
  -e NEO4J_AUTH=neo4j/dengue123 \
  -e dbms_security_auth__enabled=false \
  neo4j-dengue:local || error "Failed to start Neo4j container"

step "Waiting for Neo4j to start (this may take a minute)..."
sleep 20  # Give Neo4j time to initialize
success "Neo4j container started"

step "Starting API container..."
# Use matching Neo4j credentials
podman run -d --name dengue-api \
  --network dengue-dev-network \
  -p ${API_TEST_PORT}:8000 \
  -e NEO4J_URI=bolt://neo4j-dengue:7687 \
  -e NEO4J_USER=neo4j \
  -e NEO4J_PASSWORD=dengue123 \
  dengue-api:local || error "Failed to start API container"
success "API container started"

# Start other containers if they're built
if podman image exists dengue-frontend:local; then
    step "Starting Frontend container..."
    podman run -d --name dengue-frontend \
      --network dengue-dev-network \
      -p ${FRONTEND_TEST_PORT}:8080 \
      dengue-frontend:local || echo "Note: Frontend container start skipped or failed"
fi

if podman image exists dengue-agent-workflow:local; then
    step "Starting Agent Workflow container..."
    podman run -d --name dengue-agent-workflow \
      --network dengue-dev-network \
      -p ${AGENT_WORKFLOW_TEST_PORT}:8080 \
      -e NEO4J_URI=bolt://neo4j-dengue:7687 \
      -e NEO4J_USER=neo4j \
      -e NEO4J_PASSWORD=dengue123 \
      -e KNOWLEDGE_GRAPH_API=http://dengue-api:8000 \
      dengue-agent-workflow:local || echo "Note: Agent Workflow container start skipped or failed"
fi

if podman image exists dengue-predictive-model:local; then
    step "Starting Predictive Model container..."
    podman run -d --name dengue-predictive-model \
      --network dengue-dev-network \
      -p ${PREDICTIVE_MODEL_TEST_PORT}:8080 \
      -e NEO4J_URI=bolt://neo4j-dengue:7687 \
      -e NEO4J_USER=neo4j \
      -e NEO4J_PASSWORD=dengue123 \
      -e KNOWLEDGE_GRAPH_API=http://dengue-api:8000 \
      dengue-predictive-model:local || echo "Note: Predictive Model container start skipped or failed"
fi

if podman image exists dengue-table-rag:local; then
    step "Starting Table RAG container..."
    podman run -d --name dengue-table-rag \
      --network dengue-dev-network \
      -p ${TABLE_RAG_TEST_PORT}:8080 \
      -e NEO4J_URI=bolt://neo4j-dengue:7687 \
      -e NEO4J_USER=neo4j \
      -e NEO4J_PASSWORD=dengue123 \
      -e KNOWLEDGE_GRAPH_API=http://dengue-api:8000 \
      dengue-table-rag:local || echo "Note: Table RAG container start skipped or failed"
fi

cd "$ROOT_DIR"

section "RUNNING THE KNOWLEDGE GRAPH PIPELINE"

step "Executing the knowledge graph pipeline to load data..."
podman exec dengue-api python -m app.scripts.load_schema || echo "Note: Knowledge graph pipeline skipped or failed"

section "LOCAL DEVELOPMENT INFORMATION"

echo -e "Your local development environment is now set up!\n"
echo -e "Local Services:"
echo -e "---------------"
echo -e "1. Neo4j Browser: http://localhost:${NEO4J_TEST_PORT}"
echo -e "   - Username: neo4j, Password: dengue123 (auth disabled for development)"
echo -e ""
echo -e "2. API Documentation: http://localhost:${API_TEST_PORT}/docs"
echo -e "   - Swagger UI for the knowledge graph API"
echo -e ""

if podman container exists dengue-frontend; then
    echo -e "3. Frontend: http://localhost:${FRONTEND_TEST_PORT}"
    echo -e "   - Web interface for the dengue knowledge graph"
    echo -e ""
fi

if podman container exists dengue-agent-workflow; then
    echo -e "4. Agent Workflow API: http://localhost:${AGENT_WORKFLOW_TEST_PORT}/docs"
    echo -e "   - Documentation for the agent workflow service"
    echo -e ""
fi

if podman container exists dengue-predictive-model; then
    echo -e "5. Predictive Model API: http://localhost:${PREDICTIVE_MODEL_TEST_PORT}/docs"
    echo -e "   - Documentation for the predictive model service"
    echo -e ""
fi

if podman container exists dengue-table-rag; then
    echo -e "6. Table RAG API: http://localhost:${TABLE_RAG_TEST_PORT}/docs"
    echo -e "   - Documentation for the table RAG service"
    echo -e ""
fi

echo -e "For local development in VSCode, use the Python: Select Interpreter command"
echo -e "and select .venv/bin/python from each service directory."
echo -e ""
echo -e "To shut down all services, run: podman stop \$(podman ps -aq) && podman rm \$(podman ps -aq)"
echo -e "To restart individual services: podman start <container-name>"

echo -e ""
success "Setup completed! Happy coding!"
