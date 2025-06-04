#!/usr/bin/env python3
"""
Connect remaining dengue symptoms to their corresponding ontology terms.
This script uses direct mappings based on clinical research documents.
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

def connect_symptom_to_ontology_term(driver, symptom_name, term_id):
    """Connect a symptom to an ontology term."""
    query = """
    MATCH (s:Symptom {name: $symptom_name})
    MATCH (ot:OntologyTerm {id: $term_id})
    MERGE (s)-[:HAS_ONTOLOGY_TERM]->(ot)
    RETURN s.name AS symptom, ot.name AS ontology_term
    """
    result = run_cypher(driver, query, {
        "symptom_name": symptom_name,
        "term_id": term_id
    })
    
    if result:
        logging.info(f"Connected Symptom '{result[0]['symptom']}' to OntologyTerm '{result[0]['ontology_term']}'")
        return True
    return False

def get_unconnected_symptoms(driver):
    """Get symptoms without ontology connections."""
    query = """
    MATCH (s:Symptom)
    WHERE NOT (s)-[:HAS_ONTOLOGY_TERM]->()
    RETURN s.name AS name
    """
    return run_cypher(driver, query)

def main():
    """Main function to connect symptoms to ontology terms."""
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
        )
        logging.info(f"Successfully connected to Neo4j at {NEO4J_URI}")
        
        # Get unconnected symptoms
        unconnected_symptoms = get_unconnected_symptoms(driver)
        logging.info(f"Found {len(unconnected_symptoms)} unconnected symptoms")
        
        # Define mappings based on CDC and WHO clinical guidance
        # Source references:
        # - https://www.cdc.gov/dengue/hcp/clinical-signs/index.html
        # - https://www.who.int/publications/i/item/9789241547871
        # These are research-supported mappings for dengue symptoms
        symptom_to_term_mappings = {
            # General clinical manifestation of dengue
            "Fever": ["IDODEN_0000049"],  # clinical manifestation of dengue
            "Headache": ["IDODEN_0000049"],  # clinical manifestation of dengue
            "Retro-orbital Pain": ["IDODEN_0000049"],  # clinical manifestation of dengue
            "Myalgia": ["IDODEN_0000049"],  # clinical manifestation of dengue
            
            # Warning signs - more severe clinical manifestations
            "Severe Abdominal Pain": ["IDODEN_0000049", "IDODEN_0003756"],  # clinical manifestation of dengue, occurrence of severe dengue fever
            "Persistent Vomiting": ["IDODEN_0000049", "IDODEN_0003756"],  # clinical manifestation of dengue, occurrence of severe dengue fever
            
            # Hemorrhagic manifestations
            "Mucosal Bleeding": ["IDODEN_0000049", "IDODEN_0003763"],  # clinical manifestation of dengue, dengue hemorrhagic fever
            "Severe Bleeding": ["IDODEN_0003763"],  # dengue hemorrhagic fever
            
            # Shock manifestation
            "Shock": ["IDODEN_0003764"]  # dengue shock syndrome
        }
        
        # Fallback to clinical manifestation if no specific mapping
        default_term_id = "IDODEN_0000049"  # clinical manifestation of dengue
        
        # Connect symptoms to terms
        connections_made = 0
        for symptom in unconnected_symptoms:
            symptom_name = symptom.get("name")
            
            # Skip if missing data
            if not symptom_name:
                continue
            
            # Get term IDs for this symptom
            term_ids = symptom_to_term_mappings.get(symptom_name, [default_term_id])
            
            # Connect to each term
            for term_id in term_ids:
                if connect_symptom_to_ontology_term(driver, symptom_name, term_id):
                    connections_made += 1
        
        logging.info(f"Connected {connections_made} symptom-ontology term relationships")
        
        # Close the Neo4j connection
        driver.close()
        logging.info("Neo4j driver closed")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
