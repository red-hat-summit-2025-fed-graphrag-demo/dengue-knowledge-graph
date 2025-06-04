"""
Dengue Knowledge Graph API
FastAPI service for accessing and querying the Neo4j-based knowledge graph
"""
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase, basic_auth
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

# Import config, models, utils, and routers using relative paths
from .config import settings
from .models import GraphInfo, SampleQuery
from .utils import setup_logging, get_neo4j_driver
from .routes import router, graph_router, dengue_router, ontology_router

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dengue Knowledge Graph API",
    description="API for querying the Dengue Knowledge Graph stored in Neo4j",
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

# --- Neo4j Connection Configuration ---
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")
NEO4J_AUTH = os.environ.get("NEO4J_AUTH", "basic")


# --- Database Connection ---
def get_db():
    """Get Neo4j database connection driver with appropriate authentication"""
    try:
        if NEO4J_AUTH.lower() == "none":
            # No authentication
            driver = GraphDatabase.driver(NEO4J_URI)
        else:
            # Use basic authentication
            auth = basic_auth(NEO4J_USER, NEO4J_PASSWORD)
            driver = GraphDatabase.driver(NEO4J_URI, auth=auth)
        
        # Verify connection
        driver.verify_connectivity()
        
        yield driver
        driver.close()
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j database: {e}")
        raise HTTPException(status_code=503, detail=f"Database connection error: {str(e)}")


# --- API Models ---
class GraphNode(BaseModel):
    """Representation of a Neo4j node"""
    id: str
    labels: List[str]
    properties: Dict[str, Any]


class GraphRelationship(BaseModel):
    """Representation of a Neo4j relationship"""
    id: str
    type: str
    start_node: str
    end_node: str
    properties: Dict[str, Any]


class GraphPathElement(BaseModel):
    """Element in a graph path"""
    type: str  # 'node' or 'relationship'
    data: Dict[str, Any]


class GraphPath(BaseModel):
    """Representation of a path in the graph"""
    elements: List[GraphPathElement]


class QueryRequest(BaseModel):
    """Request body for Cypher queries"""
    query: str
    parameters: Optional[Dict[str, Any]] = {}


class QueryResponse(BaseModel):
    """Response from a Cypher query"""
    results: List[Dict[str, Any]]
    count: int


# Include routers
app.include_router(router)
app.include_router(graph_router)
app.include_router(dengue_router)
app.include_router(ontology_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
