"""
Dengue Knowledge Graph API
FastAPI service for accessing and querying the Neo4j-based knowledge graph
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
import logging

# Import application modules
from .config import get_settings, configure_logging, Settings
from .routes import router, graph_router, dengue_router, ontology_router
from .database import get_db

# Configure logging
configure_logging()
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

# Define API key security
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

# Include routers
app.include_router(router)
app.include_router(graph_router, prefix="/api/v1")
app.include_router(dengue_router, prefix="/api/v1")
app.include_router(ontology_router, prefix="/api/v1")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Execute tasks when the application starts"""
    logger.info("Starting Dengue Knowledge Graph API")
    settings = get_settings()
    logger.info(f"Connecting to Neo4j at {settings.neo4j_uri}")
    
    # Log if API key authentication is enabled
    if settings.api_key:
        logger.info("API Key authentication enabled")
    else:
        logger.warning("API Key authentication disabled - consider enabling for production")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Execute tasks when the application shuts down"""
    logger.info("Shutting down Dengue Knowledge Graph API")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic service information"""
    return {
        "service": "Dengue Knowledge Graph API",
        "version": "1.0.0",
        "status": "active",
        "documentation": "/docs",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
