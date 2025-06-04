#!/usr/bin/env python3
"""
Connect existing nodes in the Dengue Knowledge Graph to relevant ontology terms.
This script uses fuzzy matching to find potential connections between existing nodes 
(e.g., symptoms, clinical classifications) and ontology terms.
"""

import os
import logging
import re
from neo4j import GraphDatabase, basic_auth
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get connection details from environment variables or use defaults
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "denguePassw0rd!")

# Similarity threshold for fuzzy matching
SIMILARITY_THRESHOLD = 0.5  # Reduced from 0.7 to 0.5 to create more connections

def similarity_score(a, b):
    """Calculate string similarity using SequenceMatcher."""
    # Ensure both inputs are strings
    a_str = str(a).lower() if a is not None else ""
    b_str = str(b).lower() if b is not None else ""
    return SequenceMatcher(None, a_str, b_str).ratio()

def run_cypher(driver, query, params=None):
    """Execute a Cypher query and return the results."""
    with driver.session() as session:
        result = session.run(query, params or {})
        return result.data()

def get_nodes_by_label(driver, label):
    """Get all nodes with a specific label."""
    query = f"""
    MATCH (n:{label})
    RETURN n.id AS id, n.name AS name
    """
    return run_cypher(driver, query)

def get_ontology_terms(driver, source=None):
    """Get all ontology terms, optionally filtered by source."""
    query = """
    MATCH (ot:OntologyTerm)
    WHERE $source IS NULL OR ot.source = $source
    RETURN ot.id AS id, ot.name AS name, ot.source AS source
    """
    return run_cypher(driver, query, {"source": source})

def connect_symptoms_to_ontology_terms(driver):
    """Connect Symptom nodes to related OntologyTerm nodes."""
    logging.info("Connecting Symptoms to Ontology Terms...")
    
    # Get all symptoms
    symptoms = get_nodes_by_label(driver, "Symptom")
    logging.info(f"Found {len(symptoms)} Symptom nodes")
    
    # Get relevant ontology terms with expanded query
    query = """
    MATCH (ot:OntologyTerm)
    WHERE toLower(ot.name) CONTAINS 'symptom' OR 
          toLower(ot.name) CONTAINS 'clinical feature' OR 
          toLower(ot.name) CONTAINS 'manifestation' OR
          toLower(ot.name) CONTAINS 'sign' OR
          toLower(ot.name) CONTAINS 'pain' OR
          toLower(ot.name) CONTAINS 'fever' OR
          toLower(ot.name) CONTAINS 'bleeding' OR
          toLower(ot.name) CONTAINS 'nausea' OR
          toLower(ot.name) CONTAINS 'vomiting' OR
          toLower(ot.name) CONTAINS 'rash' OR
          toLower(ot.name) CONTAINS 'fatigue' OR
          toLower(ot.name) CONTAINS 'headache' OR
          toLower(ot.name) CONTAINS 'dengue'
    RETURN ot.id AS id, ot.name AS name, ot.source AS source
    """
    ontology_terms = run_cypher(driver, query)
    logging.info(f"Found {len(ontology_terms)} symptom-related OntologyTerm nodes")
    
    # Direct mapping for common symptom terms
    direct_mapping = {
        "fever": ["fever", "pyrexia", "temperature"],
        "headache": ["headache", "cephalgia"],
        "rash": ["rash", "skin eruption", "maculopapular"],
        "arthralgia": ["joint pain", "arthralgia", "painful joints"],
        "myalgia": ["muscle pain", "myalgia"],
        "fatigue": ["fatigue", "tiredness", "malaise"],
        "nausea": ["nausea", "sick feeling"],
        "vomiting": ["vomiting", "emesis"],
        "abdominal pain": ["abdominal pain", "stomach pain", "belly pain"],
        "bleeding": ["bleeding", "hemorrhage", "haemorrhage", "bleed"],
        "petechiae": ["petechiae", "purpura", "small hemorrhage"]
    }
    
    # Get dengue clinical manifestation term (a good default for any symptom)
    query = """
    MATCH (ot:OntologyTerm)
    WHERE toLower(ot.name) CONTAINS 'clinical manifestation' AND toLower(ot.name) CONTAINS 'dengue'
    RETURN ot.id AS id LIMIT 1
    """
    result = run_cypher(driver, query)
    default_term_id = result[0]["id"] if result else None
    
    # Track connections for reporting
    connections = []
    
    # For each symptom, find potential matches in ontology terms
    for symptom in symptoms:
        symptom_name = symptom.get("name", "")
        if not symptom_name:
            continue
            
        symptom_name = symptom_name.lower()
        matched_terms = []
        
        # Apply direct mapping
        for symptom_key, synonyms in direct_mapping.items():
            if symptom_key in symptom_name or any(syn in symptom_name for syn in synonyms):
                # Find matching ontology terms
                direct_matches = [term for term in ontology_terms 
                                 if any(syn in term.get("name", "").lower() for syn in synonyms)]
                matched_terms.extend(direct_matches)
        
        # If no direct matches, use fuzzy matching
        if not matched_terms:
            for term in ontology_terms:
                term_name = term.get("name", "")
                if not term_name:
                    continue
                    
                term_name = term_name.lower()
                
                # Check if the symptom name is contained in the term name or vice versa
                if symptom_name in term_name or term_name in symptom_name:
                    matched_terms.append(term)
                    continue
                    
                # Check for specific symptom keywords
                symptom_keywords = symptom_name.split()
                term_keywords = term_name.split()
                
                # If any keyword matches directly
                if any(kw in term_keywords for kw in symptom_keywords):
                    matched_terms.append(term)
                    continue
                    
                # Otherwise, check similarity score
                similarity = similarity_score(symptom_name, term_name)
                if similarity >= SIMILARITY_THRESHOLD:
                    matched_terms.append(term)
        
        # If still no matches, use the default dengue clinical manifestation term
        if not matched_terms and default_term_id:
            query = """
            MATCH (ot:OntologyTerm {id: $term_id})
            RETURN ot.id AS id, ot.name AS name, ot.source AS source
            """
            result = run_cypher(driver, query, {"term_id": default_term_id})
            if result:
                matched_terms.append(result[0])
        
        # Connect symptom to matching terms
        for term in matched_terms:
            query = """
            MATCH (s:Symptom {id: $symptom_id})
            MATCH (ot:OntologyTerm {id: $term_id})
            MERGE (s)-[:HAS_ONTOLOGY_TERM]->(ot)
            RETURN s.name AS symptom, ot.name AS ontology_term
            """
            result = run_cypher(driver, query, {
                "symptom_id": symptom["id"],
                "term_id": term["id"]
            })
            
            if result:
                connections.append((result[0]["symptom"], result[0]["ontology_term"]))
                logging.info(f"Connected Symptom '{result[0]['symptom']}' to OntologyTerm '{result[0]['ontology_term']}'")
    
    return connections

def connect_clinical_classifications_to_ontology_terms(driver):
    """Connect ClinicalClassification nodes to related OntologyTerm nodes."""
    logging.info("Connecting Clinical Classifications to Ontology Terms...")
    
    # Get all clinical classifications
    classifications = get_nodes_by_label(driver, "ClinicalClassification")
    logging.info(f"Found {len(classifications)} ClinicalClassification nodes")
    
    # Get relevant ontology terms - specifically looking for severity/classification terms
    query = """
    MATCH (ot:OntologyTerm)
    WHERE toLower(ot.name) CONTAINS 'dengue' AND 
          (toLower(ot.name) CONTAINS 'severe' OR 
           toLower(ot.name) CONTAINS 'hemorrhagic' OR
           toLower(ot.name) CONTAINS 'shock' OR
           toLower(ot.name) CONTAINS 'warning' OR
           toLower(ot.name) CONTAINS 'classification')
    RETURN ot.id AS id, ot.name AS name, ot.source AS source
    """
    ontology_terms = run_cypher(driver, query)
    logging.info(f"Found {len(ontology_terms)} classification-related OntologyTerm nodes")
    
    connections = []
    
    # For each classification, find potential matches in ontology terms
    for classification in classifications:
        classification_name = classification.get("name", "")
        if not classification_name:
            continue
            
        classification_name = classification_name.lower()
        matched_terms = []
        
        for term in ontology_terms:
            term_name = term.get("name", "")
            if not term_name:
                continue
                
            term_name = term_name.lower()
            
            # Check for direct matches or subset matches
            if classification_name in term_name or term_name in classification_name:
                matched_terms.append(term)
                continue
                
            # Otherwise, check similarity score
            similarity = similarity_score(classification_name, term_name)
            if similarity >= SIMILARITY_THRESHOLD:
                matched_terms.append(term)
        
        # Connect classification to matching terms
        for term in matched_terms:
            query = """
            MATCH (c:ClinicalClassification {id: $classification_id})
            MATCH (ot:OntologyTerm {id: $term_id})
            MERGE (c)-[:HAS_ONTOLOGY_TERM]->(ot)
            RETURN c.name AS classification, ot.name AS ontology_term
            """
            result = run_cypher(driver, query, {
                "classification_id": classification["id"],
                "term_id": term["id"]
            })
            
            if result:
                connections.append((result[0]["classification"], result[0]["ontology_term"]))
                logging.info(f"Connected ClinicalClassification '{result[0]['classification']}' to OntologyTerm '{result[0]['ontology_term']}'")
    
    return connections

def connect_diagnostic_tests_to_ontology_terms(driver):
    """Connect DiagnosticTest nodes to related OntologyTerm nodes."""
    logging.info("Connecting Diagnostic Tests to Ontology Terms...")
    
    # Get all diagnostic tests
    tests = get_nodes_by_label(driver, "DiagnosticTest")
    logging.info(f"Found {len(tests)} DiagnosticTest nodes")
    
    # Filter ontology terms to those related to testing or diagnostics
    query = """
    MATCH (ot:OntologyTerm)
    WHERE toLower(ot.name) CONTAINS 'test' OR 
          toLower(ot.name) CONTAINS 'diagnostic' OR
          toLower(ot.name) CONTAINS 'elisa' OR
          toLower(ot.name) CONTAINS 'pcr'
    RETURN ot.id AS id, ot.name AS name, ot.source AS source
    """
    test_terms = run_cypher(driver, query)
    logging.info(f"Found {len(test_terms)} diagnostic-related OntologyTerm nodes")
    
    connections = []
    
    # For each test, find potential matches in ontology terms
    for test in tests:
        test_name = test.get("name", "")
        if not test_name:
            continue
            
        test_name = test_name.lower()
        matched_terms = []
        
        for term in test_terms:
            term_name = term.get("name", "")
            if not term_name:
                continue
                
            term_name = term_name.lower()
            
            # Check for direct matches or subset matches
            if test_name in term_name or term_name in test_name:
                matched_terms.append(term)
                continue
                
            # Otherwise, check similarity score
            similarity = similarity_score(test_name, term_name)
            if similarity >= SIMILARITY_THRESHOLD:
                matched_terms.append(term)
        
        # Connect test to matching terms
        for term in matched_terms:
            query = """
            MATCH (dt:DiagnosticTest {id: $test_id})
            MATCH (ot:OntologyTerm {id: $term_id})
            MERGE (dt)-[:HAS_ONTOLOGY_TERM]->(ot)
            RETURN dt.name AS test, ot.name AS ontology_term
            """
            result = run_cypher(driver, query, {
                "test_id": test["id"],
                "term_id": term["id"]
            })
            
            if result:
                connections.append((result[0]["test"], result[0]["ontology_term"]))
                logging.info(f"Connected DiagnosticTest '{result[0]['test']}' to OntologyTerm '{result[0]['ontology_term']}'")
    
    return connections

def connect_treatment_protocols_to_ontology_terms(driver):
    """Connect TreatmentProtocol nodes to related OntologyTerm nodes."""
    logging.info("Connecting Treatment Protocols to Ontology Terms...")
    
    # Get all treatment protocols
    protocols = get_nodes_by_label(driver, "TreatmentProtocol")
    logging.info(f"Found {len(protocols)} TreatmentProtocol nodes")
    
    # Filter ontology terms to those related to treatment
    query = """
    MATCH (ot:OntologyTerm)
    WHERE toLower(ot.name) CONTAINS 'treatment'
    RETURN ot.id AS id, ot.name AS name, ot.source AS source
    """
    treatment_terms = run_cypher(driver, query)
    logging.info(f"Found {len(treatment_terms)} treatment-related OntologyTerm nodes")
    
    connections = []
    
    # For each protocol, find potential matches in ontology terms
    for protocol in protocols:
        protocol_name = protocol.get("name", "")
        if not protocol_name:
            continue
            
        protocol_name = protocol_name.lower()
        matched_terms = []
        
        for term in treatment_terms:
            term_name = term.get("name", "")
            if not term_name:
                continue
                
            term_name = term_name.lower()
            
            # Connect all treatment protocols to general treatment terms
            if "dengue" in term_name and "treatment" in term_name:
                matched_terms.append(term)
        
        # Connect protocol to matching terms
        for term in matched_terms:
            query = """
            MATCH (tp:TreatmentProtocol {id: $protocol_id})
            MATCH (ot:OntologyTerm {id: $term_id})
            MERGE (tp)-[:HAS_ONTOLOGY_TERM]->(ot)
            RETURN tp.name AS protocol, ot.name AS ontology_term
            """
            result = run_cypher(driver, query, {
                "protocol_id": protocol["id"],
                "term_id": term["id"]
            })
            
            if result:
                connections.append((result[0]["protocol"], result[0]["ontology_term"]))
                logging.info(f"Connected TreatmentProtocol '{result[0]['protocol']}' to OntologyTerm '{result[0]['ontology_term']}'")
    
    return connections

def connect_risk_factors_to_ontology_terms(driver):
    """Connect RiskFactor nodes to related OntologyTerm nodes."""
    logging.info("Connecting Risk Factors to Ontology Terms...")
    
    # Get all risk factors
    risk_factors = get_nodes_by_label(driver, "RiskFactor")
    logging.info(f"Found {len(risk_factors)} RiskFactor nodes")
    
    # Get relevant risk factor terms
    query = """
    MATCH (ot:OntologyTerm)
    WHERE toLower(ot.name) CONTAINS 'risk' OR 
          toLower(ot.name) CONTAINS 'susceptibility' OR
          toLower(ot.name) CONTAINS 'predisposition'
    RETURN ot.id AS id, ot.name AS name, ot.source AS source
    """
    ontology_terms = run_cypher(driver, query)
    logging.info(f"Found {len(ontology_terms)} risk-related OntologyTerm nodes")
    
    connections = []
    
    # For each risk factor, find potential matches in ontology terms
    for risk_factor in risk_factors:
        risk_factor_name = risk_factor.get("name", "")
        if not risk_factor_name:
            continue
            
        risk_factor_name = risk_factor_name.lower()
        matched_terms = []
        
        for term in ontology_terms:
            term_name = term.get("name", "")
            if not term_name:
                continue
                
            term_name = term_name.lower()
            
            # Check for direct matches or subset matches
            if risk_factor_name in term_name or term_name in risk_factor_name:
                matched_terms.append(term)
                continue
                
            # Otherwise, check similarity score
            similarity = similarity_score(risk_factor_name, term_name)
            if similarity >= SIMILARITY_THRESHOLD:
                matched_terms.append(term)
        
        # Connect risk factor to matching terms
        for term in matched_terms:
            query = """
            MATCH (rf:RiskFactor {id: $risk_factor_id})
            MATCH (ot:OntologyTerm {id: $term_id})
            MERGE (rf)-[:HAS_ONTOLOGY_TERM]->(ot)
            RETURN rf.name AS risk_factor, ot.name AS ontology_term
            """
            result = run_cypher(driver, query, {
                "risk_factor_id": risk_factor["id"],
                "term_id": term["id"]
            })
            
            if result:
                connections.append((result[0]["risk_factor"], result[0]["ontology_term"]))
                logging.info(f"Connected RiskFactor '{result[0]['risk_factor']}' to OntologyTerm '{result[0]['ontology_term']}'")
    
    return connections

def connect_vector_to_ontology_terms(driver):
    """Connect Vector nodes to related OntologyTerm nodes."""
    logging.info("Connecting Vectors to Ontology Terms...")
    
    # Get all vectors
    vectors = get_nodes_by_label(driver, "Vector")
    logging.info(f"Found {len(vectors)} Vector nodes")
    
    # Get generic dengue vector term
    query = """
    MATCH (ot:OntologyTerm)
    WHERE toLower(ot.name) = 'dengue vector'
    RETURN ot.id AS id, ot.name AS name, ot.source AS source
    """
    dengue_vector_terms = run_cypher(driver, query)
    
    # Get vector related ontology terms with expanded query
    query = """
    MATCH (ot:OntologyTerm)
    WHERE toLower(ot.name) CONTAINS 'vector' OR 
          toLower(ot.name) CONTAINS 'mosquito' OR
          toLower(ot.name) CONTAINS 'aedes' OR
          toLower(ot.name) CONTAINS 'transmission' OR
          toLower(ot.name) CONTAINS 'aegypti' OR
          toLower(ot.name) CONTAINS 'albopictus'
    RETURN ot.id AS id, ot.name AS name, ot.source AS source
    """
    vector_terms = run_cypher(driver, query)
    logging.info(f"Found {len(vector_terms)} vector-related OntologyTerm nodes")
    
    # Direct mapping for common vector species
    vector_mapping = {
        "aedes aegypti": ["aedes aegypti", "aegypti", "yellow fever mosquito"],
        "aedes albopictus": ["aedes albopictus", "albopictus", "asian tiger mosquito"]
    }
    
    connections = []
    
    # For each vector, find potential matches in ontology terms
    for vector in vectors:
        vector_name = vector.get("name", "")
        if not vector_name:
            continue
            
        vector_name = vector_name.lower()
        matched_terms = []
        
        # Apply direct mapping
        for vector_key, synonyms in vector_mapping.items():
            if vector_key in vector_name or any(syn in vector_name for syn in synonyms):
                # Find matching ontology terms
                direct_matches = [term for term in vector_terms 
                                 if any(syn in term.get("name", "").lower() for syn in synonyms)]
                matched_terms.extend(direct_matches)
        
        # If no direct matches, try standard matching
        if not matched_terms:
            for term in vector_terms:
                term_name = term.get("name", "")
                if not term_name:
                    continue
                    
                term_name = term_name.lower()
                
                # Check for direct matches or subset matches
                if vector_name in term_name or term_name in vector_name:
                    matched_terms.append(term)
                    continue
                
                # Check for species matches - be more specific with mosquito species
                vector_parts = vector_name.split()
                if len(vector_parts) >= 2:
                    genus = vector_parts[0]
                    species = vector_parts[1] if len(vector_parts) > 1 else ""
                    
                    if genus in term_name or species in term_name:
                        matched_terms.append(term)
                        continue
                    
                # Otherwise, check similarity score
                similarity = similarity_score(vector_name, term_name)
                if similarity >= SIMILARITY_THRESHOLD:
                    matched_terms.append(term)
        
        # Add generic dengue vector term if we have one
        if dengue_vector_terms and not matched_terms:
            matched_terms.extend(dengue_vector_terms)
            
        # Connect vector to matching terms
        for term in matched_terms:
            query = """
            MATCH (v:Vector {id: $vector_id})
            MATCH (ot:OntologyTerm {id: $term_id})
            MERGE (v)-[:HAS_ONTOLOGY_TERM]->(ot)
            RETURN v.name AS vector, ot.name AS ontology_term
            """
            result = run_cypher(driver, query, {
                "vector_id": vector["id"],
                "term_id": term["id"]
            })
            
            if result:
                connections.append((result[0]["vector"], result[0]["ontology_term"]))
                logging.info(f"Connected Vector '{result[0]['vector']}' to OntologyTerm '{result[0]['ontology_term']}'")
    
    return connections

def main():
    """Main function to connect nodes to ontology terms."""
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
        )
        logging.info(f"Successfully connected to Neo4j at {NEO4J_URI}")
        
        # Connect different node types to ontology terms
        symptom_connections = connect_symptoms_to_ontology_terms(driver)
        classification_connections = connect_clinical_classifications_to_ontology_terms(driver)
        test_connections = connect_diagnostic_tests_to_ontology_terms(driver)
        protocol_connections = connect_treatment_protocols_to_ontology_terms(driver)
        risk_factor_connections = connect_risk_factors_to_ontology_terms(driver)
        vector_connections = connect_vector_to_ontology_terms(driver)
        
        # Summarize connections
        total_connections = (
            len(symptom_connections) +
            len(classification_connections) +
            len(test_connections) +
            len(protocol_connections) +
            len(risk_factor_connections) +
            len(vector_connections)
        )
        
        logging.info(f"Connected {len(symptom_connections)} Symptoms to OntologyTerms")
        logging.info(f"Connected {len(classification_connections)} Clinical Classifications to OntologyTerms")
        logging.info(f"Connected {len(test_connections)} Diagnostic Tests to OntologyTerms")
        logging.info(f"Connected {len(protocol_connections)} Treatment Protocols to OntologyTerms")
        logging.info(f"Connected {len(risk_factor_connections)} Risk Factors to OntologyTerms")
        logging.info(f"Connected {len(vector_connections)} Vectors to OntologyTerms")
        logging.info(f"Total: {total_connections} new connections created")
        
        # Close the Neo4j connection
        driver.close()
        logging.info("Neo4j driver closed")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
