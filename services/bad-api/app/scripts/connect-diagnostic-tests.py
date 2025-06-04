#!/usr/bin/env python3
"""
Connect remaining diagnostic test nodes to their corresponding ontology terms.
Based on research and available ontology terms in the database.
"""

import os
import logging
from neo4j import GraphDatabase, basic_auth

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get connection details from environment variables or use defaults
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "denguePassw0rd!")

def run_cypher(driver, query, params=None):
    """Execute a Cypher query and return the results."""
    with driver.session() as session:
        result = session.run(query, params or {})
        return result.data()

def connect_test_to_ontology_term(driver, test_name, term_id):
    """Connect a diagnostic test to an ontology term."""
    query = """
    MATCH (d:DiagnosticTest {name: $test_name})
    MATCH (ot:OntologyTerm {id: $term_id})
    MERGE (d)-[:HAS_ONTOLOGY_TERM]->(ot)
    RETURN d.name AS test_name, ot.name AS ontology_term
    """
    result = run_cypher(driver, query, {
        "test_name": test_name,
        "term_id": term_id
    })
    
    if result:
        logging.info(f"Connected DiagnosticTest '{result[0]['test_name']}' to OntologyTerm '{result[0]['ontology_term']}'")
        return True
    else:
        logging.warning(f"Failed to connect DiagnosticTest '{test_name}' to OntologyTerm '{term_id}'")
        return False

def connect_diagnostic_tests(driver):
    """Connect all unconnected diagnostic tests to appropriate ontology terms."""
    # Define mappings based on available terms and test types
    test_mappings = {
        "NAAT (RT-PCR)": [
            "IDODEN_0000084"  # dengue fever diagnosis
        ],
        "NS1 Antigen Test": [
            "IDODEN_0000253",  # dengue virus antigen detection
            "IDODEN_0000283",  # dengue rapid diagnostic test product
            "IDODEN_0000286"   # Rapid Dengue Test (Dengue NS1 AG)
        ],
        "IgM Antibody Test": [
            "IDODEN_0000287",  # Dengue IgM and IgG Combo Rapid Test
            "IDODEN_0000283"   # dengue rapid diagnostic test product
        ]
    }
    
    # Get all unconnected diagnostic tests
    query = """
    MATCH (d:DiagnosticTest)
    WHERE NOT EXISTS((d)-[:HAS_ONTOLOGY_TERM]->())
    RETURN d.name AS name
    """
    tests = run_cypher(driver, query)
    
    total_connections = 0
    for test in tests:
        test_name = test.get("name")
        
        # Skip if test has no name
        if not test_name:
            continue
        
        # Get ontology term IDs for this test
        term_ids = test_mappings.get(test_name, [])
        
        # If no specific mapping, use general diagnosis term
        if not term_ids:
            term_ids = ["IDODEN_0000084"]  # dengue fever diagnosis
        
        # Connect to each term
        for term_id in term_ids:
            if connect_test_to_ontology_term(driver, test_name, term_id):
                total_connections += 1
    
    logging.info(f"Connected {total_connections} diagnostic test-ontology term relationships")
    return total_connections

def main():
    """Main function to connect diagnostic tests to ontology terms."""
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
        )
        logging.info(f"Successfully connected to Neo4j at {NEO4J_URI}")
        
        # Connect diagnostic tests
        connect_diagnostic_tests(driver)
        
        # Close the Neo4j connection
        driver.close()
        logging.info("Neo4j driver closed")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
