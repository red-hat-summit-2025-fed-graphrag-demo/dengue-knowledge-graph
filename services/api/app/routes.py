"""
API route definitions for the Dengue Knowledge Graph API
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, status
from typing import List, Dict, Any, Optional
import logging

from .database import get_db, Neo4jDatabase
from .models import (
    GraphInfo, 
    SampleQuery, 
    CypherQuery, 
    DengueSymptom,
    DengueClassification,
    DiagnosticTest,
    Treatment,
    Prevention,
    Region,
    DengueCaseInput,
    DengueCase,
    OntologyTerm,
    SearchResult,
    GraphStats,
    QueryRequest,
    QueryResponse
)

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
async def health_check(db: Neo4jDatabase = Depends(get_db)):
    """Health check endpoint to verify Neo4j connection"""
    try:
        # Simple query to verify database is responding
        result = db.execute_query("RETURN 1 as n")
        if result and result[0].get("n") == 1:
            return {"status": "healthy", "database": "connected"}
        return {"status": "degraded", "database": "connected but query failed"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=f"Database health check failed: {str(e)}"
        )


# --- Graph query routes ---
@graph_router.post("/query", response_model=QueryResponse, tags=["Graph Operations"])
async def run_query(request: QueryRequest, db: Neo4jDatabase = Depends(get_db)):
    """Run a custom Cypher query against the Neo4j database"""
    try:
        records = db.execute_query(request.query, request.parameters)
        return {"results": records, "count": len(records)}
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Query execution failed: {str(e)}"
        )


@graph_router.get("/info", response_model=GraphInfo, tags=["Graph Operations"])
async def get_graph_info(db: Neo4jDatabase = Depends(get_db)):
    """Get overview information about the graph database"""
    try:
        # Get node labels
        labels_result = db.execute_query("CALL db.labels()")
        labels = [record["label"] for record in labels_result]
        
        # Get relationship types
        rel_types_result = db.execute_query("CALL db.relationshipTypes()")
        rel_types = [record["relationshipType"] for record in rel_types_result]
        
        # Get property keys
        prop_keys_result = db.execute_query("CALL db.propertyKeys()")
        prop_keys = [record["propertyKey"] for record in prop_keys_result]
        
        # Get node and relationship counts
        counts_result = db.execute_query("""
            MATCH (n) 
            OPTIONAL MATCH ()-[r]->() 
            RETURN count(DISTINCT n) AS node_count, count(DISTINCT r) AS rel_count
        """)
        
        return GraphInfo(
            labels=labels,
            relationship_types=rel_types,
            property_keys=prop_keys,
            node_count=counts_result[0]["node_count"],
            relationship_count=counts_result[0]["rel_count"]
        )
    except Exception as e:
        logger.error(f"Error retrieving graph info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving graph information: {str(e)}"
        )


@graph_router.get("/stats", response_model=GraphStats, tags=["Graph Operations"])
async def get_graph_stats(db: Neo4jDatabase = Depends(get_db)):
    """Get detailed statistics about the graph"""
    try:
        # Get node counts by label
        node_counts = {}
        labels_result = db.execute_query("CALL db.labels()")
        labels = [record["label"] for record in labels_result]
        
        for label in labels:
            count_result = db.execute_query(f"MATCH (n:`{label}`) RETURN count(n) as count")
            node_counts[label] = count_result[0]["count"]
        
        # Get relationship counts by type
        rel_counts = {}
        rel_types_result = db.execute_query("CALL db.relationshipTypes()")
        rel_types = [record["relationshipType"] for record in rel_types_result]
        
        for rel_type in rel_types:
            count_result = db.execute_query(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count")
            rel_counts[rel_type] = count_result[0]["count"]
        
        # Calculate average degree if there are nodes
        avg_degree = None
        if sum(node_counts.values()) > 0:
            avg_degree_result = db.execute_query("""
                MATCH (n)
                WITH n, size((n)--()) as degree
                RETURN avg(degree) AS avg_degree
            """)
            avg_degree = avg_degree_result[0]["avg_degree"]
        
        return GraphStats(
            node_count_by_label=node_counts,
            relationship_count_by_type=rel_counts,
            avg_degree=avg_degree,
            density=None  # Could be calculated if needed
        )
    except Exception as e:
        logger.error(f"Error retrieving graph stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving graph statistics: {str(e)}"
        )


@graph_router.get("/nodes/{label}", tags=["Graph Operations"])
async def get_nodes_by_label(
    label: str, 
    limit: int = Query(100, ge=1, le=1000),
    properties: Optional[List[str]] = Query(None),
    db: Neo4jDatabase = Depends(get_db)
):
    """Retrieve nodes by label from the knowledge graph"""
    try:
        # Build properties to return based on optional parameter
        return_clause = "n" if not properties else "{" + ", ".join([f"{p}: n.{p}" for p in properties]) + "}"
        
        query = f"""
        MATCH (n:{label})
        RETURN {return_clause}
        LIMIT $limit
        """
        result = db.execute_query(query, {"limit": limit})
        
        if not properties:
            nodes = []
            for record in result:
                # Handle the case where 'n' is a Neo4j node
                node_data = record.get("n", {})
                if hasattr(node_data, "id") and callable(getattr(node_data, "id")):
                    # It's a Neo4j node object
                    nodes.append({
                        "id": str(node_data.id),
                        "properties": dict(node_data.items())
                    })
                else:
                    # It's already a dict
                    nodes.append(node_data)
        else:
            nodes = result
            
        return {"nodes": nodes, "count": len(nodes)}
    except Exception as e:
        logger.error(f"Error retrieving nodes with label {label}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Error retrieving nodes: {str(e)}"
        )


@graph_router.get("/relationships/{type}", tags=["Graph Operations"])
async def get_relationships_by_type(
    type: str, 
    limit: int = Query(100, ge=1, le=1000),
    db: Neo4jDatabase = Depends(get_db)
):
    """Retrieve relationships by type from the knowledge graph"""
    try:
        query = f"""
        MATCH (source)-[r:{type}]->(target)
        RETURN source, r, target
        LIMIT $limit
        """
        result = db.execute_query(query, {"limit": limit})
        relationships = []
        
        for record in result:
            source = record["source"]
            rel = record["r"]
            target = record["target"]
            
            # Convert Neo4j objects to dictionaries
            source_data = dict(source.items()) if hasattr(source, "items") else source
            target_data = dict(target.items()) if hasattr(target, "items") else target
            rel_data = dict(rel.items()) if hasattr(rel, "items") else rel
            
            relationships.append({
                "source": {
                    "id": str(source.id) if hasattr(source, "id") else "unknown",
                    "labels": list(source.labels) if hasattr(source, "labels") else [],
                    "properties": source_data
                },
                "relationship": {
                    "id": str(rel.id) if hasattr(rel, "id") else "unknown",
                    "type": rel.type if hasattr(rel, "type") else type,
                    "properties": rel_data
                },
                "target": {
                    "id": str(target.id) if hasattr(target, "id") else "unknown",
                    "labels": list(target.labels) if hasattr(target, "labels") else [],
                    "properties": target_data
                }
            })
            
        return {"relationships": relationships, "count": len(relationships)}
    except Exception as e:
        logger.error(f"Error retrieving relationships of type {type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Error retrieving relationships: {str(e)}"
        )


# --- Dengue specific routes ---
@dengue_router.get("/symptoms", response_model=List[DengueSymptom], tags=["Dengue Data"])
async def get_dengue_symptoms(db: Neo4jDatabase = Depends(get_db)):
    """Get symptoms associated with Dengue fever"""
    try:
        query = """
        MATCH (s:Symptom)-[:ASSOCIATED_WITH]->(d:Disease {name: 'Dengue'})
        RETURN s.name as name, s.description as description, s.severity as severity
        ORDER BY s.severity DESC, s.name
        """
        result = db.execute_query(query)
        symptoms = [DengueSymptom(**record) for record in result]
        return symptoms
    except Exception as e:
        logger.error(f"Error retrieving dengue symptoms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving symptoms: {str(e)}"
        )


@dengue_router.get("/classifications", response_model=List[DengueClassification], tags=["Dengue Data"])
async def get_dengue_classifications(db: Neo4jDatabase = Depends(get_db)):
    """Get Dengue fever classifications and their diagnostic criteria"""
    try:
        query = """
        MATCH (c:Classification)-[:SUB_TYPE_OF]->(d:Disease {name: 'Dengue'})
        OPTIONAL MATCH (c)<-[:INDICATES]-(s:Symptom)
        WITH c, collect(s.name) as symptoms
        RETURN c.name as name, c.description as description, symptoms,
               c.diagnostic_criteria as diagnostic_criteria
        ORDER BY c.severity DESC, c.name
        """
        result = db.execute_query(query)
        classifications = [DengueClassification(**record) for record in result]
        return classifications
    except Exception as e:
        logger.error(f"Error retrieving dengue classifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving classifications: {str(e)}"
        )


@dengue_router.get("/diagnostics", response_model=List[DiagnosticTest], tags=["Dengue Data"])
async def get_dengue_diagnostics(db: Neo4jDatabase = Depends(get_db)):
    """Get diagnostic tests used for Dengue fever"""
    try:
        query = """
        MATCH (dt:DiagnosticTest)-[:USED_FOR]->(d:Disease {name: 'Dengue'})
        RETURN dt.name as name, dt.description as description, 
               dt.methodology as methodology, dt.accuracy as accuracy,
               dt.recommended_timing as recommended_timing
        ORDER BY dt.accuracy DESC, dt.name
        """
        result = db.execute_query(query)
        diagnostics = [DiagnosticTest(**record) for record in result]
        return diagnostics
    except Exception as e:
        logger.error(f"Error retrieving diagnostic tests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving diagnostic tests: {str(e)}"
        )


@dengue_router.get("/treatments", response_model=List[Treatment], tags=["Dengue Data"])
async def get_dengue_treatments(db: Neo4jDatabase = Depends(get_db)):
    """Get treatment protocols for Dengue fever"""
    try:
        query = """
        MATCH (t:Treatment)-[:TREATS]->(d:Disease {name: 'Dengue'})
        OPTIONAL MATCH (t)-[:RECOMMENDED_FOR]->(c:Classification)
        RETURN t.name as name, t.description as description, 
               c.name as for_classification,
               t.contraindications as contraindications
        ORDER BY t.name
        """
        result = db.execute_query(query)
        treatments = [Treatment(**record) for record in result]
        return treatments
    except Exception as e:
        logger.error(f"Error retrieving treatments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving treatments: {str(e)}"
        )


@dengue_router.get("/prevention", response_model=List[Prevention], tags=["Dengue Data"])
async def get_dengue_prevention(db: Neo4jDatabase = Depends(get_db)):
    """Get prevention measures for Dengue fever"""
    try:
        query = """
        MATCH (p:Prevention)-[:PREVENTS]->(d:Disease {name: 'Dengue'})
        RETURN p.name as name, p.description as description, 
               p.effectiveness as effectiveness,
               p.implementation_level as implementation_level
        ORDER BY p.effectiveness DESC, p.name
        """
        result = db.execute_query(query)
        prevention = [Prevention(**record) for record in result]
        return prevention
    except Exception as e:
        logger.error(f"Error retrieving prevention measures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving prevention measures: {str(e)}"
        )


@dengue_router.get("/regions", response_model=List[Region], tags=["Dengue Data"])
async def get_dengue_regions(db: Neo4jDatabase = Depends(get_db)):
    """Get geographical regions with Dengue presence"""
    try:
        query = """
        MATCH (r:Region)-[:HAS_DISEASE]->(d:Disease {name: 'Dengue'})
        RETURN r.name as name, r.description as description, 
               r.risk_level as risk_level,
               r.endemic_serotypes as endemic_serotypes,
               r.population_at_risk as population_at_risk
        ORDER BY r.risk_level DESC, r.name
        """
        result = db.execute_query(query)
        regions = [Region(**record) for record in result]
        return regions
    except Exception as e:
        logger.error(f"Error retrieving regions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving regions: {str(e)}"
        )


# --- Search routes ---
@router.get("/search", tags=["Search"])
async def search_knowledge_graph(
    query: str = Query(..., description="Search term"),
    node_types: Optional[str] = Query(None, description="Comma-separated list of node labels to search"),
    limit: int = Query(20, ge=1, le=100),
    db: Neo4jDatabase = Depends(get_db)
):
    """Search the knowledge graph for nodes matching the query text"""
    try:
        # Parse node types if provided
        labels = []
        if node_types:
            labels = [label.strip() for label in node_types.split(",")]
        
        # Build label filter
        label_filter = ""
        if labels:
            label_filter = "WHERE " + " OR ".join([f"n:{label}" for label in labels])
        
        # Full-text search query
        cypher_query = f"""
        MATCH (n)
        {label_filter}
        WHERE 
          toLower(n.name) CONTAINS toLower($query) OR
          toLower(coalesce(n.description, '')) CONTAINS toLower($query)
        RETURN n, labels(n) as node_labels
        LIMIT $limit
        """
        
        result = db.execute_query(cypher_query, {"query": query, "limit": limit})
        search_results = []
        
        for record in result:
            node = record["n"]
            node_labels = record["node_labels"]
            
            search_results.append({
                "id": str(node.id) if hasattr(node, "id") else "unknown",
                "labels": node_labels,
                "properties": dict(node.items()) if hasattr(node, "items") else node,
                "result_type": "node"
            })
        
        return {"results": search_results, "count": len(search_results)}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Search failed: {str(e)}"
        )


# --- Ontology routes ---
@ontology_router.get("/terms/{concept}", response_model=List[OntologyTerm], tags=["Ontology"])
async def get_ontology_terms(
    concept: str,
    limit: int = Query(100, ge=1, le=1000),
    db: Neo4jDatabase = Depends(get_db)
):
    """Get ontology terms related to a concept"""
    try:
        query = """
        MATCH (t:OntologyTerm)
        WHERE toLower(t.name) CONTAINS toLower($concept) OR
              toLower(t.term_id) CONTAINS toLower($concept) OR
              ANY(syn IN t.synonyms WHERE toLower(syn) CONTAINS toLower($concept))
        RETURN t.term_id as term_id, t.name as name, 
               t.definition as definition, t.synonyms as synonyms,
               t.ontology_source as ontology_source
        LIMIT $limit
        """
        result = db.execute_query(query, {"concept": concept, "limit": limit})
        terms = [OntologyTerm(**record) for record in result]
        return terms
    except Exception as e:
        logger.error(f"Error retrieving ontology terms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving ontology terms: {str(e)}"
        )
