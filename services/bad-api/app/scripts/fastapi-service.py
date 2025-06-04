#!/usr/bin/env python3
"""
Dengue Knowledge Graph - FastAPI Service

This script provides a FastAPI service for interacting with the Dengue Knowledge Graph.
It offers endpoints for querying the graph, visualization, and information retrieval.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from neo4j import GraphDatabase, basic_auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j") 
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")

# Initialize FastAPI app
app = FastAPI(
    title="Dengue Knowledge Graph API",
    description="API for accessing and visualizing the Dengue Knowledge Graph",
    version="1.0.0"
)

# --- Models ---
class Node(BaseModel):
    id: int
    labels: List[str]
    properties: Dict[str, Any]

class Relationship(BaseModel):
    id: int
    type: str
    start_node: Dict[str, Any]
    end_node: Dict[str, Any]
    properties: Dict[str, Any]

class GraphSummary(BaseModel):
    node_counts: Dict[str, int]
    relationship_counts: Dict[str, int]
    total_nodes: int
    total_relationships: int

class SearchResult(BaseModel):
    nodes: List[Node]
    relationships: List[Relationship]
    query_time_ms: float

# --- Database Connection ---
def get_db():
    """Get Neo4j database driver."""
    driver = GraphDatabase.driver(
        NEO4J_URI, 
        auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
    )
    try:
        yield driver
    finally:
        driver.close()

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint providing HTML dashboard."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dengue Knowledge Graph</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }
            header {
                background-color: #0066cc;
                color: white;
                padding: 20px;
                margin-bottom: 20px;
            }
            h1 {
                margin: 0;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .card {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 20px;
                margin-bottom: 20px;
                background-color: #f8f9fa;
            }
            .btn {
                display: inline-block;
                background-color: #0066cc;
                color: white;
                padding: 8px 16px;
                text-decoration: none;
                border-radius: 4px;
                margin-right: 10px;
                margin-bottom: 10px;
            }
            .btn:hover {
                background-color: #0052a3;
            }
            .endpoints {
                margin-top: 30px;
            }
            .endpoint {
                margin-bottom: 15px;
                padding-bottom: 15px;
                border-bottom: 1px solid #eee;
            }
        </style>
    </head>
    <body>
        <header>
            <div class="container">
                <h1>Dengue Knowledge Graph</h1>
                <p>Interactive API for exploring the Dengue Fever Knowledge Graph</p>
            </div>
        </header>
        
        <div class="container">
            <div class="card">
                <h2>Graph Overview</h2>
                <p>The Dengue Knowledge Graph contains information about Dengue Fever, its symptoms, diagnosis, treatment, and epidemiology.</p>
                <a href="/graph/summary" class="btn">View Graph Summary</a>
                <a href="/graph/visualization" class="btn">Interactive Visualization</a>
            </div>
            
            <div class="card">
                <h2>Quick Search</h2>
                <form action="/search" method="get">
                    <input type="text" name="q" placeholder="Search the graph..." style="padding: 8px; width: 70%; margin-right: 10px;">
                    <button type="submit" class="btn">Search</button>
                </form>
            </div>
            
            <div class="endpoints">
                <h2>API Endpoints</h2>
                
                <div class="endpoint">
                    <h3>Graph Data</h3>
                    <p><a href="/graph/nodes" class="btn">Nodes</a> - Get all nodes in the graph</p>
                    <p><a href="/graph/relationships" class="btn">Relationships</a> - Get all relationships in the graph</p>
                    <p><a href="/graph/summary" class="btn">Summary</a> - Get graph statistics and summary</p>
                </div>
                
                <div class="endpoint">
                    <h3>Disease Information</h3>
                    <p><a href="/diseases" class="btn">Diseases</a> - Get all diseases</p>
                    <p><a href="/diseases/symptoms" class="btn">Symptoms</a> - Get diseases with their symptoms</p>
                    <p><a href="/diseases/classifications" class="btn">Classifications</a> - Get disease classifications</p>
                </div>
                
                <div class="endpoint">
                    <h3>Epidemiology</h3>
                    <p><a href="/regions" class="btn">Regions</a> - Get geographical regions</p>
                    <p><a href="/vectors" class="btn">Vectors</a> - Get disease vectors</p>
                    <p><a href="/outbreaks" class="btn">Outbreaks</a> - Get outbreak information</p>
                </div>
                
                <div class="endpoint">
                    <h3>Clinical Information</h3>
                    <p><a href="/diagnostics" class="btn">Diagnostics</a> - Get diagnostic tests</p>
                    <p><a href="/treatments" class="btn">Treatments</a> - Get treatment protocols</p>
                    <p><a href="/prevention" class="btn">Prevention</a> - Get prevention measures</p>
                </div>
            </div>
            
            <div class="card">
                <h2>Documentation</h2>
                <p>For complete API documentation, visit the <a href="/docs">API Docs</a>.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

@app.get("/health")
async def health_check(db: GraphDatabase.driver = Depends(get_db)):
    """Health check endpoint."""
    try:
        with db.session() as session:
            result = session.run("RETURN 1 AS result")
            result.single()
        return {"status": "healthy", "database_connection": "ok"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/graph/summary", response_model=GraphSummary)
async def get_graph_summary(db: GraphDatabase.driver = Depends(get_db)):
    """Get summary statistics for the graph."""
    try:
        with db.session() as session:
            # Get node counts by label
            result = session.run("""
                CALL db.labels() YIELD label
                CALL apoc.cypher.run('MATCH (n:' + $label + ') RETURN count(n) as count', {}) YIELD value
                RETURN $label AS label, value.count AS count
            """)
            node_counts = {record["label"]: record["count"] for record in result}
            
            # Get relationship counts by type
            result = session.run("""
                CALL db.relationshipTypes() YIELD relationshipType
                CALL apoc.cypher.run('MATCH ()-[r:' + $relationshipType + ']->() RETURN count(r) as count', {}) YIELD value
                RETURN $relationshipType AS type, value.count AS count
            """)
            relationship_counts = {record["type"]: record["count"] for record in result}
            
            # Get total counts
            result = session.run("MATCH (n) RETURN count(n) AS count")
            total_nodes = result.single()["count"]
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            total_relationships = result.single()["count"]
            
            return {
                "node_counts": node_counts,
                "relationship_counts": relationship_counts,
                "total_nodes": total_nodes,
                "total_relationships": total_relationships
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/nodes", response_model=List[Node])
async def get_all_nodes(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    labels: Optional[str] = Query(None, description="Comma-separated list of labels to filter by"),
    db: GraphDatabase.driver = Depends(get_db)
):
    """Get all nodes in the graph with pagination and filtering."""
    try:
        with db.session() as session:
            query = "MATCH (n)"
            
            # Apply label filter if provided
            if labels:
                label_list = [label.strip() for label in labels.split(",")]
                label_where = " WHERE " + " OR ".join([f"n:{label}" for label in label_list])
                query += label_where
            
            query += f" RETURN n, labels(n) as labels ORDER BY id(n) SKIP {offset} LIMIT {limit}"
            
            result = session.run(query)
            nodes = []
            
            for record in result:
                node = record["n"]
                node_labels = record["labels"]
                node_id = node.id
                node_props = dict(node)
                
                nodes.append({
                    "id": node_id,
                    "labels": node_labels,
                    "properties": node_props
                })
            
            return nodes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/relationships", response_model=List[Relationship])
async def get_all_relationships(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    types: Optional[str] = Query(None, description="Comma-separated list of relationship types to filter by"),
    db: GraphDatabase.driver = Depends(get_db)
):
    """Get all relationships in the graph with pagination and filtering."""
    try:
        with db.session() as session:
            query = "MATCH (n)-[r]->(m)"
            
            # Apply type filter if provided
            if types:
                type_list = [type.strip() for type in types.split(",")]
                type_where = " WHERE " + " OR ".join([f"type(r) = '{t}'" for t in type_list])
                query += type_where
            
            query += f"""
                RETURN id(r) AS id, 
                       type(r) AS type, 
                       id(n) AS start_id, 
                       labels(n) AS start_labels, 
                       id(m) AS end_id, 
                       labels(m) AS end_labels, 
                       properties(r) AS properties 
                ORDER BY id(r) 
                SKIP {offset} LIMIT {limit}
            """
            
            result = session.run(query)
            relationships = []
            
            for record in result:
                rel = {
                    "id": record["id"],
                    "type": record["type"],
                    "start_node": {
                        "id": record["start_id"],
                        "labels": record["start_labels"]
                    },
                    "end_node": {
                        "id": record["end_id"],
                        "labels": record["end_labels"]
                    },
                    "properties": record["properties"]
                }
                
                relationships.append(rel)
            
            return relationships
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=SearchResult)
async def search_graph(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=500),
    db: GraphDatabase.driver = Depends(get_db)
):
    """Search the graph for nodes and relationships matching the query."""
    try:
        import time
        start_time = time.time()
        
        with db.session() as session:
            # Search for nodes
            node_query = """
            CALL db.index.fulltext.queryNodes('diseaseAndSymptomSearch', $query) YIELD node, score
            RETURN node, labels(node) as labels, score
            ORDER BY score DESC
            LIMIT toInteger($limit / 2)
            """
            
            node_result = session.run(node_query, {"query": q, "limit": limit})
            nodes = []
            
            for record in node_result:
                node = record["node"]
                node_labels = record["labels"]
                node_id = node.id
                node_props = dict(node)
                
                nodes.append({
                    "id": node_id,
                    "labels": node_labels,
                    "properties": node_props
                })
            
            # Find relationships connecting the found nodes
            relationship_query = """
            UNWIND $nodeIds AS nodeId
            MATCH (n)-[r]-(m)
            WHERE id(n) = nodeId
            RETURN id(r) AS id, 
                   type(r) AS type, 
                   id(n) AS start_id, 
                   labels(n) AS start_labels, 
                   id(m) AS end_id, 
                   labels(m) AS end_labels, 
                   properties(r) AS properties 
            LIMIT $limit
            """
            
            node_ids = [node["id"] for node in nodes]
            
            rel_result = session.run(relationship_query, {"nodeIds": node_ids, "limit": limit})
            relationships = []
            
            for record in rel_result:
                rel = {
                    "id": record["id"],
                    "type": record["type"],
                    "start_node": {
                        "id": record["start_id"],
                        "labels": record["start_labels"]
                    },
                    "end_node": {
                        "id": record["end_id"],
                        "labels": record["end_labels"]
                    },
                    "properties": record["properties"]
                }
                
                relationships.append(rel)
            
            end_time = time.time()
            query_time_ms = (end_time - start_time) * 1000
            
            return {
                "nodes": nodes,
                "relationships": relationships,
                "query_time_ms": query_time_ms
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/visualization", response_class=HTMLResponse)
async def graph_visualization():
    """Return an interactive HTML visualization of the graph."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dengue Knowledge Graph Visualization</title>
        <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
        <style>
            body, html {
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                height: 100%;
                width: 100%;
            }
            #container {
                display: flex;
                height: 100%;
                width: 100%;
            }
            #sidebar {
                width: 300px;
                background-color: #f8f9fa;
                padding: 20px;
                box-sizing: border-box;
                overflow-y: auto;
                border-right: 1px solid #ddd;
            }
            #graph {
                flex-grow: 1;
                height: 100%;
            }
            .controls {
                margin-bottom: 20px;
            }
            .controls button {
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 8px 16px;
                margin-right: 5px;
                cursor: pointer;
                border-radius: 4px;
            }
            .controls button:hover {
                background-color: #0052a3;
            }
            .info-panel {
                margin-top: 20px;
                max-height: 500px;
                overflow-y: auto;
                padding: 10px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            .filter-section {
                margin-bottom: 15px;
            }
            .filter-section h3 {
                margin-top: 0;
                margin-bottom: 10px;
            }
            .checkbox-list {
                max-height: 150px;
                overflow-y: auto;
                padding: 5px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            .checkbox-item {
                margin-bottom: 5px;
            }
            h1 {
                margin-top: 0;
                font-size: 20px;
            }
            h2 {
                font-size: 16px;
                margin-top: 15px;
            }
            input[type="text"] {
                width: 100%;
                padding: 8px;
                margin-bottom: 10px;
                box-sizing: border-box;
            }
        </style>
    </head>
    <body>
        <div id="container">
            <div id="sidebar">
                <h1>Dengue Knowledge Graph</h1>
                
                <div class="controls">
                    <button onclick="loadGraph()">Load Graph</button>
                    <button onclick="fitGraph()">Fit View</button>
                </div>
                
                <div class="filter-section">
                    <h3>Search</h3>
                    <input type="text" id="search-input" placeholder="Search nodes..." onkeyup="filterNodes()">
                </div>
                
                <div class="filter-section">
                    <h3>Node Types</h3>
                    <div id="node-filters" class="checkbox-list">
                        <!-- Will be populated dynamically -->
                    </div>
                </div>
                
                <div class="filter-section">
                    <h3>Relationship Types</h3>
                    <div id="rel-filters" class="checkbox-list">
                        <!-- Will be populated dynamically -->
                    </div>
                </div>
                
                <div id="info-panel" class="info-panel">
                    <p>Select a node or relationship to see details.</p>
                </div>
            </div>
            <div id="graph"></div>
        </div>
        
        <script>
            let network;
            let allNodes = [];
            let allEdges = [];
            let nodeTypes = new Set();
            let edgeTypes = new Set();
            
            // Function to load graph data
            async function loadGraph() {
                try {
                    document.getElementById('info-panel').innerHTML = 'Loading graph data...';
                    
                    // Fetch nodes
                    const nodesResponse = await axios.get('/graph/nodes?limit=500');
                    allNodes = nodesResponse.data.map(node => {
                        const label = node.properties.name || node.labels.join(':') + ':' + node.id;
                        return {
                            id: node.id,
                            label: label,
                            title: JSON.stringify(node.properties, null, 2),
                            group: node.labels[0],
                            data: node
                        };
                    });
                    
                    // Extract node types
                    nodeTypes = new Set();
                    allNodes.forEach(node => {
                        node.data.labels.forEach(label => nodeTypes.add(label));
                    });
                    
                    // Fetch relationships
                    const edgesResponse = await axios.get('/graph/relationships?limit=1000');
                    allEdges = edgesResponse.data.map(rel => {
                        return {
                            id: 'e' + rel.id,
                            from: rel.start_node.id,
                            to: rel.end_node.id,
                            label: rel.type,
                            title: JSON.stringify(rel.properties, null, 2),
                            arrows: 'to',
                            data: rel
                        };
                    });
                    
                    // Extract relationship types
                    edgeTypes = new Set();
                    allEdges.forEach(edge => {
                        edgeTypes.add(edge.label);
                    });
                    
                    // Update filters
                    populateFilters();
                    
                    // Create network
                    createNetwork(allNodes, allEdges);
                    
                    document.getElementById('info-panel').innerHTML = `
                        <h2>Graph Loaded</h2>
                        <p>Nodes: ${allNodes.length}</p>
                        <p>Relationships: ${allEdges.length}</p>
                        <p>Click on nodes or relationships to see details.</p>
                    `;
                    
                } catch (error) {
                    console.error('Error loading graph data:', error);
                    document.getElementById('info-panel').innerHTML = `
                        <h2>Error Loading Data</h2>
                        <p>${error.message || 'Unknown error'}</p>
                    `;
                }
            }
            
            function populateFilters() {
                // Populate node type filters
                const nodeFiltersEl = document.getElementById('node-filters');
                nodeFiltersEl.innerHTML = '';
                
                Array.from(nodeTypes).sort().forEach(type => {
                    const item = document.createElement('div');
                    item.className = 'checkbox-item';
                    item.innerHTML = `
                        <input type="checkbox" id="node-${type}" value="${type}" checked onchange="applyFilters()">
                        <label for="node-${type}">${type}</label>
                    `;
                    nodeFiltersEl.appendChild(item);
                });
                
                // Populate relationship type filters
                const relFiltersEl = document.getElementById('rel-filters');
                relFiltersEl.innerHTML = '';
                
                Array.from(edgeTypes).sort().forEach(type => {
                    const item = document.createElement('div');
                    item.className = 'checkbox-item';
                    item.innerHTML = `
                        <input type="checkbox" id="rel-${type}" value="${type}" checked onchange="applyFilters()">
                        <label for="rel-${type}">${type}</label>
                    `;
                    relFiltersEl.appendChild(item);
                });
            }
            
            function applyFilters() {
                // Get selected node types
                const selectedNodeTypes = Array.from(nodeTypes)
                    .filter(type => document.getElementById(`node-${type}`).checked);
                
                // Get selected relationship types
                const selectedRelTypes = Array.from(edgeTypes)
                    .filter(type => document.getElementById(`rel-${type}`).checked);
                
                // Filter nodes
                const filteredNodes = allNodes.filter(node => {
                    return node.data.labels.some(label => selectedNodeTypes.includes(label));
                });
                
                // Get IDs of visible nodes
                const visibleNodeIds = new Set(filteredNodes.map(node => node.id));
                
                // Filter relationships
                const filteredEdges = allEdges.filter(edge => {
                    return selectedRelTypes.includes(edge.label) &&
                           visibleNodeIds.has(edge.from) &&
                           visibleNodeIds.has(edge.to);
                });
                
                // Update the network
                updateNetwork(filteredNodes, filteredEdges);
            }
            
            function filterNodes() {
                const searchTerm = document.getElementById('search-input').value.toLowerCase();
                
                if (!searchTerm) {
                    applyFilters();
                    return;
                }
                
                // Filter nodes by search term
                const filteredNodes = allNodes.filter(node => {
                    // Check name property first
                    if (node.data.properties.name && 
                        node.data.properties.name.toLowerCase().includes(searchTerm)) {
                        return true;
                    }
                    
                    // Then check other properties
                    for (const [key, value] of Object.entries(node.data.properties)) {
                        if (String(value).toLowerCase().includes(searchTerm)) {
                            return true;
                        }
                    }
                    
                    // Check labels
                    return node.data.labels.some(label => 
                        label.toLowerCase().includes(searchTerm));
                });
                
                // Get IDs of visible nodes
                const visibleNodeIds = new Set(filteredNodes.map(node => node.id));
                
                // Filter relationships
                const filteredEdges = allEdges.filter(edge => 
                    visibleNodeIds.has(edge.from) && visibleNodeIds.has(edge.to));
                
                // Update the network
                updateNetwork(filteredNodes, filteredEdges);
            }
            
            function createNetwork(nodes, edges) {
                const container = document.getElementById('graph');
                
                const data = {
                    nodes: new vis.DataSet(nodes),
                    edges: new vis.DataSet(edges)
                };
                
                const options = {
                    nodes: {
                        shape: 'dot',
                        size: 16,
                        font: {
                            size: 12
                        }
                    },
                    edges: {
                        font: {
                            size: 10,
                            align: 'middle'
                        },
                        smooth: {
                            type: 'continuous'
                        }
                    },
                    physics: {
                        stabilization: false,
                        barnesHut: {
                            gravitationalConstant: -80000,
                            springConstant: 0.001,
                            springLength: 200
                        }
                    },
                    groups: {
                        Disease: { color: { background: '#ff9999', border: '#ff0000' } },
                        Symptom: { color: { background: '#ffcc99', border: '#ff9933' } },
                        ClinicalClassification: { color: { background: '#ffff99', border: '#ffff33' } },
                        Region: { color: { background: '#99ff99', border: '#33ff33' } },
                        Vector: { color: { background: '#99ffff', border: '#33ffff' } },
                        DiagnosticTest: { color: { background: '#9999ff', border: '#3333ff' } },
                        PreventionMeasure: { color: { background: '#ff99ff', border: '#ff33ff' } }
                    },
                    interaction: {
                        hover: true,
                        tooltipDelay: 200
                    }
                };
                
                network = new vis.Network(container, data, options);
                
                // Network events
                network.on('selectNode', function(params) {
                    const nodeId = params.nodes[0];
                    const node = allNodes.find(n => n.id === nodeId);
                    
                    if (node) {
                        const properties = Object.entries(node.data.properties)
                            .map(([key, value]) => `<tr><td>${key}</td><td>${value}</td></tr>`)
                            .join('');
                            
                        document.getElementById('info-panel').innerHTML = `
                            <h2>Node: ${node.label}</h2>
                            <p>Type: ${node.data.labels.join(', ')}</p>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr><th style="text-align: left; padding: 4px; border-bottom: 1px solid #ddd;">Property</th><th style="text-align: left; padding: 4px; border-bottom: 1px solid #ddd;">Value</th></tr>
                                ${properties}
                            </table>
                        `;
                    }
                });
                
                network.on('selectEdge', function(params) {
                    const edgeId = params.edges[0];
                    const edge = allEdges.find(e => e.id === edgeId);
                    
                    if (edge) {
                        const properties = Object.entries(edge.data.properties)
                            .map(([key, value]) => `<tr><td>${key}</td><td>${value}</td></tr>`)
                            .join('');
                            
                        document.getElementById('info-panel').innerHTML = `
                            <h2>Relationship: ${edge.label}</h2>
                            <p>From: ${edge.data.start_node.id} (${edge.data.start_node.labels.join(', ')})</p>
                            <p>To: ${edge.data.end_node.id} (${edge.data.end_node.labels.join(', ')})</p>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr><th style="text-align: left; padding: 4px; border-bottom: 1px solid #ddd;">Property</th><th style="text-align: left; padding: 4px; border-bottom: 1px solid #ddd;">Value</th></tr>
                                ${properties || '<tr><td colspan="2">No properties</td></tr>'}
                            </table>
                        `;
                    }
                });
            }
            
            function updateNetwork(nodes, edges) {
                if (!network) return;
                
                network.setData({
                    nodes: new vis.DataSet(nodes),
                    edges: new vis.DataSet(edges)
                });
            }
            
            function fitGraph() {
                if (network) {
                    network.fit();
                }
            }
            
            // Load graph on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadGraph();
            });
        </script>
    </body>
    </html>
    """
    return html

# --- Domain-Specific Endpoints ---
@app.get("/diseases", response_model=List[Dict[str, Any]])
async def get_diseases(db: GraphDatabase.driver = Depends(get_db)):
    """Get all diseases."""
    try:
        with db.session() as session:
            result = session.run("""
                MATCH (d:Disease)
                RETURN d.name AS name, 
                       d.description AS description,
                       d.icd10_code AS icd10_code,
                       d.pathogen AS pathogen,
                       d.transmission AS transmission,
                       d.incubation_period AS incubation_period
            """)
            
            diseases = []
            for record in result:
                disease = {k: v for k, v in record.items() if v is not None}
                diseases.append(disease)
                
            return diseases
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/diseases/symptoms", response_model=List[Dict[str, Any]])
async def get_diseases_with_symptoms(db: GraphDatabase.driver = Depends(get_db)):
    """Get all diseases with their symptoms."""
    try:
        with db.session() as session:
            result = session.run("""
                MATCH (d:Disease)-[r:HAS_SYMPTOM]->(s:Symptom)
                RETURN d.name AS disease_name,
                       collect({name: s.name, description: s.description, frequency: r.frequency}) AS symptoms
            """)
            
            diseases = []
            for record in result:
                disease = {
                    "disease": record["disease_name"],
                    "symptoms": record["symptoms"]
                }
                diseases.append(disease)
                
            return diseases
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/regions", response_model=List[Dict[str, Any]])
async def get_regions(db: GraphDatabase.driver = Depends(get_db)):
    """Get all geographical regions."""
    try:
        with db.session() as session:
            result = session.run("""
                MATCH (r:Region)
                OPTIONAL MATCH (r)-[:HAS_ENDEMIC_DISEASE]->(d:Disease)
                RETURN r.name AS name,
                       r.country AS country,
                       r.region_type AS region_type,
                       r.population AS population,
                       r.area_km2 AS area_km2,
                       collect(d.name) AS endemic_diseases
            """)
            
            regions = []
            for record in result:
                region = {k: v for k, v in record.items() if v is not None}
                regions.append(region)
                
            return regions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)