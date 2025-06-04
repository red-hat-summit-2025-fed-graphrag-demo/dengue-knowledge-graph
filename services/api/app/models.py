"""
Pydantic models for the Dengue Knowledge Graph API
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


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
    type: str = Field(..., description="Element type: 'node' or 'relationship'")
    data: Dict[str, Any]


class GraphPath(BaseModel):
    """Representation of a path in the graph"""
    elements: List[GraphPathElement]


class GraphInfo(BaseModel):
    """Basic information about the graph structure and size"""
    labels: List[str] = Field(..., description="List of all node labels in the graph")
    relationship_types: List[str] = Field(..., description="List of all relationship types")
    property_keys: List[str] = Field(..., description="List of all property keys")
    node_count: int = Field(..., description="Total number of nodes")
    relationship_count: int = Field(..., description="Total number of relationships")


class SampleQuery(BaseModel):
    """Parameters for generating sample graph data"""
    node_label: str = Field(..., description="Label for sample nodes to create")
    num_nodes: int = Field(default=10, description="Number of sample nodes to create")
    relationship_type: Optional[str] = Field(default=None, description="Type of relationships to create between sample nodes")
    num_relationships: int = Field(default=0, description="Number of sample relationships to create")


class CypherQuery(BaseModel):
    """Represents a Cypher query and its parameters"""
    query: str = Field(..., description="The Cypher query string")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Parameters for the Cypher query")


class QueryRequest(BaseModel):
    """Request body for Cypher queries"""
    query: str = Field(..., description="Cypher query to execute")
    parameters: Optional[Dict[str, Any]] = Field(
        default={}, description="Query parameters"
    )


class QueryResponse(BaseModel):
    """Response from a Cypher query"""
    results: List[Dict[str, Any]] = Field(..., description="Query results")
    count: int = Field(..., description="Number of results returned")


class DengueSymptom(BaseModel):
    """Dengue symptom model"""
    name: str
    description: Optional[str] = None
    severity: Optional[str] = None


class DengueClassification(BaseModel):
    """Dengue fever classification model"""
    name: str
    description: str
    symptoms: List[str]
    diagnostic_criteria: Optional[List[str]] = None


class DiagnosticTest(BaseModel):
    """Diagnostic test model"""
    name: str
    description: Optional[str] = None
    methodology: Optional[str] = None
    accuracy: Optional[float] = None
    recommended_timing: Optional[str] = None


class Treatment(BaseModel):
    """Treatment protocol model"""
    name: str
    description: Optional[str] = None
    for_classification: Optional[str] = None
    contraindications: Optional[List[str]] = None


class Prevention(BaseModel):
    """Prevention measure model"""
    name: str
    description: Optional[str] = None
    effectiveness: Optional[str] = None
    implementation_level: Optional[str] = None  # individual, community, government


class Region(BaseModel):
    """Geographical region model"""
    name: str
    description: Optional[str] = None
    risk_level: Optional[str] = None
    endemic_serotypes: Optional[List[str]] = None
    population_at_risk: Optional[int] = None


class DengueCaseInput(BaseModel):
    """Dengue case input model"""
    symptoms: List[str]
    diagnostic_test: Optional[str] = None
    region: Optional[str] = None
    outcome: Optional[str] = None


class DengueCase(BaseModel):
    """Dengue case model"""
    id: str
    symptoms: List[str]
    diagnostic_test: Optional[str] = None
    region: Optional[str] = None
    outcome: Optional[str] = None


class OntologyTerm(BaseModel):
    """Represents a term from an ontology (e.g., DOID, OBO)"""
    term_id: str = Field(..., description="Unique identifier for the term (e.g., DOID:1234)")
    name: str = Field(..., description="The human-readable name of the term")
    definition: Optional[str] = Field(default=None, description="The definition or description of the term")
    synonyms: Optional[List[str]] = Field(default=[], description="Synonyms for the term")
    ontology_source: Optional[str] = Field(default=None, description="Source ontology (e.g., DOID, GO, HPO)")


class SearchResult(BaseModel):
    """Represents a single result from a search query"""
    node: Optional[GraphNode] = Field(default=None, description="Matching node, if applicable")
    relationship: Optional[GraphRelationship] = Field(default=None, description="Matching relationship, if applicable")
    path: Optional[GraphPath] = Field(default=None, description="Matching path, if applicable")
    score: Optional[float] = Field(default=None, description="Relevance score for the result")
    result_type: str = Field(..., description="Type of result (e.g., 'node', 'relationship', 'path')")


class GraphStats(BaseModel):
    """Detailed statistics about the graph"""
    node_count_by_label: Dict[str, int] = Field(..., description="Count of nodes for each label")
    relationship_count_by_type: Dict[str, int] = Field(..., description="Count of relationships for each type")
    avg_degree: Optional[float] = Field(default=None, description="Average node degree")
    density: Optional[float] = Field(default=None, description="Graph density")
