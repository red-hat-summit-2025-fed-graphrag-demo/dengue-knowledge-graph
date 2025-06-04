"""
API route definitions for the Dengue Knowledge Graph API
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from neo4j import Driver
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from .database import get_db
from .models import (
    GraphInfo, 
    SampleQuery, 
    CypherQuery, 
    DengueCaseInput, 
    OntologyTerm, 
    SearchResult, 
    GraphStats,
    QueryRequest,
    QueryResponse
)
from .utils import generate_sample_nodes

# Configure logging
logger = logging.getLogger(__name__)

# Create routers
router = APIRouter()
graph_router = APIRouter(prefix="/graph", tags=["Graph Operations"])
dengue_router = APIRouter(prefix="/dengue", tags=["Dengue Data"])
ontology_router = APIRouter(prefix="/ontology", tags=["Ontology"])


# --- Root routes ---
@router.get("/", tags=["Service Info"])
async def root():
    """API root endpoint with service information"""
    return {
        "service": "Dengue Knowledge Graph API",
        "version": "1.0.0",
        "status": "active",
        "documentation": "/docs",
    }


@router.get("/health", tags=["Service Info"])
async def health_check(driver: Driver = Depends(get_db)):
    """Health check endpoint to verify Neo4j connection"""
    try:
        # Simple query to verify database is responding
        with driver.session() as session:
            result = session.run("RETURN 1 as n").single()
            if result and result.get("n") == 1:
                return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database health check failed: {str(e)}")


# --- Graph query routes ---
@graph_router.post("/query", response_model=QueryResponse, tags=["Graph Operations"])
async def run_query(request: QueryRequest, driver: Driver = Depends(get_db)):
    """Run a custom Cypher query against the Neo4j database"""
    try:
        with driver.session() as session:
            result = session.run(request.query, request.parameters)
            records = [record.data() for record in result]
            return {"results": records, "count": len(records)}
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")


@graph_router.get("/nodes/{label}", tags=["Graph Operations"])
async def get_nodes_by_label(
    label: str, 
    limit: int = Query(100, ge=1, le=1000),
    properties: Optional[List[str]] = Query(None),
    driver: Driver = Depends(get_db)
):
    """Retrieve nodes by label from the knowledge graph"""
    try:
        with driver.session() as session:
            # Build properties to return based on optional parameter
            return_clause = "n" if not properties else "{" + ", ".join([f"{p}: n.{p}" for p in properties]) + "}"
            
            query = f"""
            MATCH (n:{label})
            RETURN {return_clause}
            LIMIT $limit
            """
            result = session.run(query, {"limit": limit})
            
            if not properties:
                nodes = [{"id": record["n"].id, "properties": dict(record["n"].items())} 
                        for record in result]
            else:
                nodes = [dict(record) for record in result]
                
            return {"nodes": nodes, "count": len(nodes)}
    except Exception as e:
        logger.error(f"Error retrieving nodes with label {label}: {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving nodes: {str(e)}")


@graph_router.get("/relationships/{type}", tags=["Graph Operations"])
async def get_relationships_by_type(
    type: str, 
    limit: int = Query(100, ge=1, le=1000),
    driver: Driver = Depends(get_db)
):
    """Retrieve relationships by type from the knowledge graph"""
    try:
        with driver.session() as session:
            query = f"""
            MATCH ()-[r:{type}]->()
            RETURN startNode(r) as source, r, endNode(r) as target
            LIMIT $limit
            """
            result = session.run(query, {"limit": limit})
            relationships = []
            
            for record in result:
                relationships.append({
                    "id": record["r"].id,
                    "type": record["r"].type,
                    "properties": dict(record["r"].items()),
                    "source": {
                        "id": record["source"].id,
                        "labels": list(record["source"].labels),
                        "properties": dict(record["source"].items())
                    },
                    "target": {
                        "id": record["target"].id,
                        "labels": list(record["target"].labels),
                        "properties": dict(record["target"].items())
                    }
                })
                
            return {"relationships": relationships, "count": len(relationships)}
    except Exception as e:
        logger.error(f"Error retrieving relationships of type {type}: {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving relationships: {str(e)}")


# --- Dengue specific routes ---
@dengue_router.get("/symptoms", tags=["Dengue Data"])
async def get_dengue_symptoms(driver: Driver = Depends(get_db)):
    """Get symptoms associated with Dengue fever"""
    try:
        with driver.session() as session:
            query = """
            MATCH (s:Symptom)-[:ASSOCIATED_WITH]->(d:Disease {name: 'Dengue'})
            RETURN s.name as name, s.description as description, s.severity as severity
            ORDER BY s.severity DESC, s.name
            """
            result = session.run(query)
            symptoms = [dict(record) for record in result]
            return {"symptoms": symptoms, "count": len(symptoms)}
    except Exception as e:
        logger.error(f"Error retrieving dengue symptoms: {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving symptoms: {str(e)}")


@dengue_router.get("/classifications", tags=["Dengue Data"])
async def get_dengue_classifications(driver: Driver = Depends(get_db)):
    """Get Dengue fever classifications and their diagnostic criteria"""
    try:
        with driver.session() as session:
            query = """
            MATCH (c:Classification)-[:SUB_TYPE_OF]->(d:Disease {name: 'Dengue'})
            OPTIONAL MATCH (c)<-[:INDICATES]-(s:Symptom)
            WITH c, collect(s.name) as symptoms
            RETURN c.name as name, c.description as description, symptoms
            ORDER BY c.severity DESC, c.name
            """
            result = session.run(query)
            classifications = [dict(record) for record in result]
            return {"classifications": classifications, "count": len(classifications)}
    except Exception as e:
        logger.error(f"Error retrieving dengue classifications: {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving classifications: {str(e)}")


@dengue_router.get("/diagnostics", tags=["Dengue Data"])
async def get_dengue_diagnostics(driver: Driver = Depends(get_db)):
    """Get diagnostic tests used for Dengue fever"""
    try:
        with driver.session() as session:
            query = """
            MATCH (dt:DiagnosticTest)-[:USED_FOR]->(d:Disease {name: 'Dengue'})
            RETURN dt.name as name, dt.description as description, 
                   dt.methodology as methodology, dt.accuracy as accuracy,
                   dt.recommended_timing as recommended_timing
            ORDER BY dt.accuracy DESC, dt.name
            """
            result = session.run(query)
            diagnostics = [dict(record) for record in result]
            return {"diagnostics": diagnostics, "count": len(diagnostics)}
    except Exception as e:
        logger.error(f"Error retrieving diagnostic tests: {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving diagnostic tests: {str(e)}")


@dengue_router.get("/treatments", tags=["Dengue Data"])
async def get_dengue_treatments(driver: Driver = Depends(get_db)):
    """Get treatment protocols for Dengue fever"""
    try:
        with driver.session() as session:
            query = """
            MATCH (t:Treatment)-[:TREATS]->(d:Disease {name: 'Dengue'})
            OPTIONAL MATCH (t)-[:RECOMMENDED_FOR]->(c:Classification)
            RETURN t.name as name, t.description as description, 
                   c.name as for_classification,
                   t.contraindications as contraindications
            ORDER BY t.name
            """
            result = session.run(query)
            treatments = [dict(record) for record in result]
            return {"treatments": treatments, "count": len(treatments)}
    except Exception as e:
        logger.error(f"Error retrieving treatment protocols: {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving treatments: {str(e)}")


@dengue_router.get("/prevention", tags=["Dengue Data"])
async def get_dengue_prevention(driver: Driver = Depends(get_db)):
    """Get prevention measures for Dengue fever"""
    try:
        with driver.session() as session:
            query = """
            MATCH (p:Prevention)-[:PREVENTS]->(d:Disease {name: 'Dengue'})
            RETURN p.name as name, p.description as description,
                   p.effectiveness as effectiveness,
                   p.implementation_level as implementation_level
            ORDER BY p.effectiveness DESC, p.name
            """
            result = session.run(query)
            prevention = [dict(record) for record in result]
            return {"prevention_measures": prevention, "count": len(prevention)}
    except Exception as e:
        logger.error(f"Error retrieving prevention measures: {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving prevention measures: {str(e)}")


@dengue_router.get("/regions", tags=["Dengue Data"])
async def get_dengue_regions(driver: Driver = Depends(get_db)):
    """Get geographical regions with Dengue presence"""
    try:
        with driver.session() as session:
            query = """
            MATCH (r:Region)-[:HAS_DISEASE]->(d:Disease {name: 'Dengue'})
            OPTIONAL MATCH (r)-[:HAS_SEROTYPE]->(s:Serotype)
            WITH r, collect(s.name) as endemic_serotypes
            RETURN r.name as name, r.description as description,
                   r.risk_level as risk_level,
                   endemic_serotypes,
                   r.population_at_risk as population_at_risk
            ORDER BY r.risk_level DESC, r.name
            """
            result = session.run(query)
            regions = [dict(record) for record in result]
            return {"regions": regions, "count": len(regions)}
    except Exception as e:
        logger.error(f"Error retrieving regions: {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving regions: {str(e)}")


# --- Ontology routes ---
@ontology_router.get("/terms/{concept}", tags=["Ontology"])
async def get_ontology_terms(
    concept: str,
    limit: int = Query(100, ge=1, le=1000),
    driver: Driver = Depends(get_db)
):
    """Get ontology terms related to a concept"""
    try:
        with driver.session() as session:
            query = """
            MATCH (o:OntologyTerm)
            WHERE o.name CONTAINS $concept OR o.description CONTAINS $concept
            RETURN o.id as id, o.name as name, o.description as description,
                   o.ontology_source as source
            LIMIT $limit
            """
            result = session.run(query, {"concept": concept, "limit": limit})
            terms = [dict(record) for record in result]
            return {"terms": terms, "count": len(terms)}
    except Exception as e:
        logger.error(f"Error retrieving ontology terms for '{concept}': {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving ontology terms: {str(e)}")


@ontology_router.get("/connected/{node_type}", tags=["Ontology"])
async def get_ontology_connections(
    node_type: str,
    limit: int = Query(100, ge=1, le=1000),
    driver: Driver = Depends(get_db)
):
    """Get domain nodes connected to ontology terms"""
    try:
        with driver.session() as session:
            query = f"""
            MATCH (n:{node_type})-[:MAPPED_TO]->(o:OntologyTerm)
            RETURN n.name as node_name, n.description as node_description,
                   o.id as ontology_id, o.name as ontology_term,
                   o.ontology_source as ontology_source
            LIMIT $limit
            """
            result = session.run(query, {"limit": limit})
            connections = [dict(record) for record in result]
            return {"connections": connections, "count": len(connections)}
    except Exception as e:
        logger.error(f"Error retrieving ontology connections for {node_type}: {e}")
        raise HTTPException(status_code=400, detail=f"Error retrieving ontology connections: {str(e)}")
