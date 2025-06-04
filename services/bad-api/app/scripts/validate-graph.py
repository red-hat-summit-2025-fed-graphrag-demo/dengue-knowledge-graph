#!/usr/bin/env python3
"""
Dengue Knowledge Graph - Validation Script

This script validates the structure and content of the Dengue Knowledge Graph
by performing a series of checks to ensure data integrity and completeness.
"""

import os
import sys
import logging
import time
from neo4j import GraphDatabase, basic_auth
import json
import networkx as nx
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j") 
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")
NEO4J_AUTH = os.environ.get("NEO4J_AUTH", "basic")  # Set to 'none' to disable auth

# Output directory for reports
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./validation_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Connect to Neo4j with retries
def connect_to_neo4j(retries=5, wait_time=5):
    """Connect to Neo4j database with retries."""
    driver = None
    
    for attempt in range(retries):
        try:
            # Configure auth based on settings
            if NEO4J_AUTH.lower() == "none":
                # No authentication
                logging.info("Connecting without authentication")
                driver = GraphDatabase.driver(NEO4J_URI)
            else:
                # Use basic authentication
                logging.info(f"Connecting with basic auth as user: {NEO4J_USER}")
                auth = basic_auth(NEO4J_USER, NEO4J_PASSWORD)
                driver = GraphDatabase.driver(NEO4J_URI, auth=auth)
                
            driver.verify_connectivity()
            logging.info(f"Successfully connected to Neo4j at {NEO4J_URI}")
            return driver
        except Exception as e:
            logging.warning(f"Connection attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                logging.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logging.error("Could not connect to Neo4j after multiple retries.")
                if driver:
                    driver.close()
                return None
    
    return None

# Validation functions
def check_node_counts(driver):
    """Check that all required node types exist and have sufficient counts."""
    min_counts = {
        "Disease": 2,  # Dengue Fever and Severe Dengue at minimum
        "Symptom": 5,  # At least 5 symptoms
        "ClinicalClassification": 3,  # The 3 clinical classifications
        "DiagnosticTest": 3,  # At least 3 diagnostic tests
        "Vector": 1,   # At least one vector
        "Region": 3,   # At least 3 regions
        "PreventionMeasure": 2  # At least 2 prevention measures
    }
    
    results = {}
    with driver.session() as session:
        # Get counts for all node labels
        result = session.run("""
            CALL db.labels() YIELD label
            CALL apoc.cypher.run('MATCH (n:' + $label + ') RETURN count(n) as count', {}) YIELD value
            RETURN $label AS label, value.count AS count
        """, {"label": label})
        
        for record in result:
            label = record["label"]
            count = record["count"]
            results[label] = count
    
    # Check if counts meet minimum requirements
    errors = []
    for label, min_count in min_counts.items():
        actual_count = results.get(label, 0)
        if actual_count < min_count:
            errors.append(f"Node type '{label}' has only {actual_count} nodes, but requires at least {min_count}")
    
    return {
        "success": len(errors) == 0,
        "node_counts": results,
        "errors": errors
    }

def check_relationship_integrity(driver):
    """Check that all nodes have appropriate relationships."""
    relation_requirements = [
        # Every Disease should have symptoms
        {
            "query": "MATCH (d:Disease) WHERE NOT (d)-[:HAS_SYMPTOM]->() RETURN d.name AS name",
            "error_template": "Disease '{name}' has no HAS_SYMPTOM relationships"
        },
        # Every Disease should have at least one classification
        {
            "query": "MATCH (d:Disease) WHERE NOT (d)-[:HAS_CLASSIFICATION]->() RETURN d.name AS name",
            "error_template": "Disease '{name}' has no HAS_CLASSIFICATION relationships"
        },
        # Every Disease should be connected to at least one diagnostic test
        {
            "query": "MATCH (d:Disease) WHERE NOT (d)-[:DIAGNOSED_BY]->() RETURN d.name AS name",
            "error_template": "Disease '{name}' has no DIAGNOSED_BY relationships"
        },
        # Every Vector should transmit some disease
        {
            "query": "MATCH (v:Vector) WHERE NOT (v)-[:TRANSMITS]->() RETURN v.name AS name",
            "error_template": "Vector '{name}' has no TRANSMITS relationships"
        }
    ]
    
    errors = []
    with driver.session() as session:
        for requirement in relation_requirements:
            result = session.run(requirement["query"])
            for record in result:
                name = record["name"]
                errors.append(requirement["error_template"].format(name=name))
    
    return {
        "success": len(errors) == 0,
        "errors": errors
    }

def generate_graph_summary(driver):
    """Generate a summary of the graph structure and statistics."""
    stats = {}
    
    with driver.session() as session:
        # Count nodes by label
        result = session.run("""
            CALL db.labels() YIELD label
            MATCH (n:`$label`) 
            RETURN $label AS label, count(n) AS count
            ORDER BY count DESC
        """)
        node_counts = {record["label"]: record["count"] for record in result}
        stats["node_counts"] = node_counts
        
        # Count relationships by type
        result = session.run("""
            CALL db.relationshipTypes() YIELD relationshipType
            MATCH ()-[r:`$relationshipType`]->() 
            RETURN $relationshipType AS type, count(r) AS count
            ORDER BY count DESC
        """)
        relationship_counts = {record["type"]: record["count"] for record in result}
        stats["relationship_counts"] = relationship_counts
        
        # Get top connected nodes
        result = session.run("""
            MATCH (n)
            WITH n, size((n)--()) AS connections
            ORDER BY connections DESC
            LIMIT 10
            RETURN labels(n) AS labels, n.name AS name, connections
        """)
        top_connected = [{"labels": record["labels"], "name": record["name"], "connections": record["connections"]} 
                         for record in result]
        stats["top_connected_nodes"] = top_connected
        
        # Get path statistics
        result = session.run("""
            MATCH path = shortestPath((d1:Disease)-[*]-(d2:Disease))
            WHERE d1 <> d2
            RETURN d1.name AS source, d2.name AS target, length(path) AS path_length
        """)
        path_stats = [{"source": record["source"], "target": record["target"], "length": record["path_length"]} 
                      for record in result]
        stats["path_statistics"] = path_stats
    
    return stats

def generate_visualization(driver):
    """Generate a visualization of the graph structure."""
    try:
        G = nx.DiGraph()
        
        with driver.session() as session:
            # Get nodes
            result = session.run("""
                MATCH (n)
                RETURN id(n) AS id, labels(n) AS labels, n.name AS name
                LIMIT 100
            """)
            for record in result:
                node_id = record["id"]
                labels = ":".join(record["labels"])
                name = record["name"] or f"Node {node_id}"
                G.add_node(node_id, labels=labels, name=name)
            
            # Get relationships
            result = session.run("""
                MATCH (n)-[r]->(m)
                RETURN id(n) AS source, id(m) AS target, type(r) AS type
                LIMIT 300
            """)
            for record in result:
                source = record["source"]
                target = record["target"]
                rel_type = record["type"]
                G.add_edge(source, target, type=rel_type)
        
        # Create visualization
        plt.figure(figsize=(20, 16))
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # Draw nodes
        node_labels = {node: f"{G.nodes[node]['name']}\n({G.nodes[node]['labels']})" 
                      for node in G.nodes()}
        nx.draw_networkx_nodes(G, pos, node_size=500, alpha=0.8, 
                             node_color='lightblue', linewidths=1, edgecolors='black')
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)
        
        # Draw edges
        edge_labels = {(u, v): d['type'] for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edges(G, pos, arrowsize=15, alpha=0.5)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6)
        
        plt.title("Dengue Knowledge Graph Structure", fontsize=20)
        plt.axis('off')
        
        # Save visualization
        viz_file = os.path.join(OUTPUT_DIR, "graph_visualization.png")
        plt.savefig(viz_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return viz_file
    except Exception as e:
        logging.error(f"Error generating visualization: {e}")
        return None

def main():
    """Main function to run all validation checks."""
    driver = connect_to_neo4j()
    
    if not driver:
        logging.error("Cannot proceed with validation - no database connection.")
        return 1
    
    try:
        logging.info("Starting validation of Dengue Knowledge Graph...")
        
        # Run validation checks
        node_count_results = check_node_counts(driver)
        relationship_results = check_relationship_integrity(driver)
        graph_summary = generate_graph_summary(driver)
        
        # Generate visualization
        viz_file = generate_visualization(driver)
        if viz_file:
            logging.info(f"Graph visualization saved to: {viz_file}")
        
        # Combine results
        validation_results = {
            "timestamp": time.time(),
            "overall_success": node_count_results["success"] and relationship_results["success"],
            "node_validation": node_count_results,
            "relationship_validation": relationship_results,
            "graph_summary": graph_summary
        }
        
        # Save results to file
        results_file = os.path.join(OUTPUT_DIR, "validation_results.json")
        with open(results_file, 'w') as f:
            json.dump(validation_results, f, indent=2)
        
        logging.info(f"Validation results saved to: {results_file}")
        
        # Print summary to console
        print("\n========== Validation Summary ==========")
        print(f"Overall Success: {'✅' if validation_results['overall_success'] else '❌'}")
        print(f"Node Count Validation: {'✅' if node_count_results['success'] else '❌'}")
        print(f"Relationship Integrity: {'✅' if relationship_results['success'] else '❌'}")
        
        if not node_count_results["success"]:
            print("\nNode Count Errors:")
            for error in node_count_results["errors"]:
                print(f"  - {error}")
        
        if not relationship_results["success"]:
            print("\nRelationship Errors:")
            for error in relationship_results["errors"]:
                print(f"  - {error}")
        
        print("\nNode Counts:")
        for label, count in graph_summary["node_counts"].items():
            print(f"  - {label}: {count}")
        
        print("\nRelationship Counts:")
        for type, count in graph_summary["relationship_counts"].items():
            print(f"  - {type}: {count}")
        
        print("========================================\n")
        
        return 0 if validation_results["overall_success"] else 1
    
    except Exception as e:
        logging.error(f"Error during validation: {e}")
        return 1
    
    finally:
        if driver:
            driver.close()
            logging.info("Neo4j driver closed.")

if __name__ == "__main__":
    sys.exit(main())