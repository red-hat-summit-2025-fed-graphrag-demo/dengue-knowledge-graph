#!/usr/bin/env python3
"""
Add reference nodes and relationships to the dengue knowledge graph.
This script extracts references from source documents and creates Reference nodes
that can be linked to knowledge nodes to provide citation support.
"""

import os
import re
import logging
from neo4j import GraphDatabase, basic_auth

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get connection details from environment variables or use defaults
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "denguePassw0rd!")

# Update source document paths to use new docs/ directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DOCUMENTS = {
    "CPG": os.path.join(SCRIPT_DIR, '../docs/dengue-synthesized-cpg-cdc-who.md'),
    "RESEARCH": os.path.join(SCRIPT_DIR, '../docs/dengue-disease-research.md')
}

def run_cypher(driver, query, params=None):
    """Execute a Cypher query and return the results."""
    with driver.session() as session:
        result = session.run(query, params or {})
        return result.data()

def extract_references_from_cpg():
    """Extract references from the synthesized CPG document."""
    references = []
    
    try:
        with open(SOURCE_DOCUMENTS["CPG"], 'r') as file:
            content = file.read()
            
            # Find the Works Cited section
            if "Works cited" in content:
                works_cited = content.split("Works cited")[1]
                
                # Extract each reference line
                lines = works_cited.strip().split('\n')
                for line in lines:
                    if line and not line.startswith("Works cited") and not line.strip() == "":
                        # Parse the reference
                        match = re.match(r'(.*?), accessed (.*?), (https?://\S+)', line)
                        if match:
                            title = match.group(1).strip()
                            access_date = match.group(2).strip()
                            url = match.group(3).strip()
                            
                            # Determine source organization
                            source_org = "Unknown"
                            if "cdc.gov" in url:
                                source_org = "CDC"
                            elif "who.int" in url:
                                source_org = "WHO"
                            elif "paho.org" in url:
                                source_org = "PAHO"
                            elif "ncbi.nlm.nih.gov" in url or "pubmed" in url:
                                source_org = "PubMed/NCBI"
                            
                            references.append({
                                "title": title,
                                "url": url,
                                "access_date": access_date,
                                "source_org": source_org,
                                "doc_source": "CPG"
                            })
                
    except Exception as e:
        logging.error(f"Error extracting CPG references: {e}")
    
    return references

def extract_references_from_research():
    """Extract references from the research document."""
    references = []
    
    try:
        with open(SOURCE_DOCUMENTS["RESEARCH"], 'r') as file:
            content = file.read()
            
            # Extract references - in this document they're throughout the file
            # Look for URL patterns
            url_pattern = r'(.*?), accessed (.*?), (https?://\S+)'
            matches = re.findall(url_pattern, content)
            
            for match in matches:
                title = match[0].strip()
                access_date = match[1].strip()
                url = match[2].strip()
                
                # Determine source organization
                source_org = "Unknown"
                if "cdc.gov" in url:
                    source_org = "CDC"
                elif "who.int" in url:
                    source_org = "WHO"
                elif "frontiers" in url or "journals" in url or "academic.oup.com" in url:
                    source_org = "Journal"
                elif "ncbi.nlm.nih.gov" in url or "pubmed" in url:
                    source_org = "PubMed/NCBI"
                
                references.append({
                    "title": title,
                    "url": url,
                    "access_date": access_date,
                    "source_org": source_org,
                    "doc_source": "Research"
                })
    
    except Exception as e:
        logging.error(f"Error extracting research references: {e}")
    
    return references

def create_reference_nodes(driver, references):
    """Create Reference nodes in the graph database."""
    created_count = 0
    
    for ref in references:
        query = """
        MERGE (r:Reference {url: $url})
        ON CREATE SET 
            r.title = $title,
            r.access_date = $access_date,
            r.source_org = $source_org,
            r.doc_source = $doc_source,
            r.id = $id
        RETURN r.title AS title
        """
        
        # Generate a unique ID for the reference
        ref_id = f"REF_{created_count + 1}"
        
        params = {
            "url": ref["url"],
            "title": ref["title"],
            "access_date": ref["access_date"],
            "source_org": ref["source_org"],
            "doc_source": ref["doc_source"],
            "id": ref_id
        }
        
        result = run_cypher(driver, query, params)
        if result:
            created_count += 1
            logging.info(f"Created/Updated Reference: {result[0]['title']}")
    
    logging.info(f"Created/Updated {created_count} Reference nodes in total")
    return created_count

def connect_references_to_clinical_nodes(driver):
    """Connect reference nodes to clinical nodes based on content analysis."""
    # Define mappings of clinical terms to reference titles/keywords
    clinical_mappings = [
        # Treatment protocols
        {
            "node_label": "TreatmentProtocol",
            "node_name": "Platelet Transfusion Protocol",
            "ref_keywords": ["platelet", "transfusion", "bleeding"]
        },
        {
            "node_label": "TreatmentProtocol",
            "node_name": "Group B IV Fluid Protocol",
            "ref_keywords": ["fluid", "management", "intravenous", "IV", "resuscitation"]
        },
        {
            "node_label": "TreatmentProtocol",
            "node_name": "Oral Fluid Management",
            "ref_keywords": ["oral", "hydration", "fluid"]
        },
        {
            "node_label": "TreatmentProtocol",
            "node_name": "Shock Fluid Resuscitation",
            "ref_keywords": ["shock", "resuscitation", "fluid", "dengue shock syndrome"]
        },
        
        # Clinical Classifications
        {
            "node_label": "ClinicalClassification",
            "node_name": "Dengue without Warning Signs",
            "ref_keywords": ["classification", "warning signs", "guidelines"]
        },
        {
            "node_label": "ClinicalClassification",
            "node_name": "Dengue with Warning Signs",
            "ref_keywords": ["classification", "warning signs", "guidelines"]
        },
        {
            "node_label": "ClinicalClassification",
            "node_name": "Severe Dengue",
            "ref_keywords": ["severe dengue", "classification", "guidelines"]
        },
        
        # Diagnostic Tests
        {
            "node_label": "DiagnosticTest",
            "node_name": "NAAT (RT-PCR)",
            "ref_keywords": ["PCR", "NAAT", "molecular", "diagnosis", "testing"]
        },
        {
            "node_label": "DiagnosticTest",
            "node_name": "NS1 Antigen Test",
            "ref_keywords": ["NS1", "antigen", "diagnosis", "testing"]
        },
        {
            "node_label": "DiagnosticTest",
            "node_name": "IgM Antibody Test",
            "ref_keywords": ["IgM", "antibody", "diagnosis", "testing", "serological"]
        },
        {
            "node_label": "DiagnosticTest",
            "node_name": "IgG Antibody Test",
            "ref_keywords": ["IgG", "antibody", "diagnosis", "testing", "serological"]
        },
        
        # Common Symptoms
        {
            "node_label": "Symptom",
            "node_name": "Fever",
            "ref_keywords": ["fever", "symptom", "clinical"]
        },
        {
            "node_label": "Symptom",
            "node_name": "Headache",
            "ref_keywords": ["headache", "symptom", "clinical"]
        },
        {
            "node_label": "Symptom",
            "node_name": "Rash",
            "ref_keywords": ["rash", "symptom", "clinical"]
        },
        {
            "node_label": "Symptom",
            "node_name": "Mucosal Bleeding",
            "ref_keywords": ["bleeding", "hemorrhagic", "mucosal", "symptom"]
        },
        {
            "node_label": "Symptom",
            "node_name": "Persistent Vomiting",
            "ref_keywords": ["vomiting", "warning sign", "symptom"]
        }
    ]
    
    total_connections = 0
    
    # Connect each clinical node to matching references
    for mapping in clinical_mappings:
        node_label = mapping["node_label"]
        node_name = mapping["node_name"]
        ref_keywords = mapping["ref_keywords"]
        
        # Find matching references based on keywords
        keyword_conditions = " OR ".join([f"toLower(r.title) CONTAINS toLower('{kw}')" for kw in ref_keywords])
        
        query = f"""
        MATCH (n:{node_label} {{name: $node_name}})
        MATCH (r:Reference)
        WHERE {keyword_conditions}
        MERGE (n)-[:HAS_REFERENCE]->(r)
        RETURN n.name AS node, r.title AS reference
        """
        
        results = run_cypher(driver, query, {"node_name": node_name})
        
        for result in results:
            logging.info(f"Connected {result['node']} to reference: {result['reference']}")
            total_connections += 1
    
    logging.info(f"Created {total_connections} connections between clinical nodes and references")
    return total_connections

def connect_who_cdc_references(driver):
    """Connect primary WHO and CDC guideline references to all clinical nodes."""
    # Get primary WHO and CDC guideline references
    query = """
    MATCH (r:Reference)
    WHERE r.source_org IN ['WHO', 'CDC', 'PAHO'] AND
          (r.title CONTAINS 'guideline' OR 
           r.title CONTAINS 'Guidelines' OR 
           r.title CONTAINS 'Pocket Guide' OR
           r.title CONTAINS 'Clinical Care')
    RETURN r.id AS id, r.title AS title
    """
    
    primary_refs = run_cypher(driver, query)
    if not primary_refs:
        logging.warning("No primary WHO/CDC guideline references found")
        return 0
    
    # Get reference IDs
    ref_ids = [ref["id"] for ref in primary_refs]
    
    # Connect to all clinical node types
    clinical_labels = ["TreatmentProtocol", "DiagnosticTest", "ClinicalClassification", "Symptom"]
    
    total_connections = 0
    
    for label in clinical_labels:
        # Connect all nodes of this type to primary references
        for ref_id in ref_ids:
            query = f"""
            MATCH (n:{label})
            MATCH (r:Reference {{id: $ref_id}})
            MERGE (n)-[:HAS_REFERENCE]->(r)
            RETURN count(*) AS count
            """
            
            result = run_cypher(driver, query, {"ref_id": ref_id})
            if result and result[0]["count"] > 0:
                count = result[0]["count"]
                total_connections += count
                logging.info(f"Connected {count} {label} nodes to reference {ref_id}")
    
    logging.info(f"Created {total_connections} connections to primary WHO/CDC references")
    return total_connections

def update_api_for_references(driver):
    """Update API schema to include reference information in queries."""
    # Create index on Reference nodes for faster lookups
    query = """
    CREATE INDEX reference_url_idx IF NOT EXISTS
    FOR (r:Reference) ON (r.url)
    """
    
    run_cypher(driver, query)
    logging.info("Created index on Reference.url property")
    
    # No other changes needed directly in the database
    # The API code will need to be updated separately
    
    return True

def main():
    """Main function to add references to the knowledge graph."""
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
        )
        logging.info(f"Successfully connected to Neo4j at {NEO4J_URI}")
        
        # Extract references from source documents
        cpg_refs = extract_references_from_cpg()
        logging.info(f"Extracted {len(cpg_refs)} references from CPG document")
        
        research_refs = extract_references_from_research()
        logging.info(f"Extracted {len(research_refs)} references from research document")
        
        all_refs = cpg_refs + research_refs
        logging.info(f"Total of {len(all_refs)} references extracted")
        
        # Create reference nodes
        create_reference_nodes(driver, all_refs)
        
        # Connect references to clinical nodes
        connect_references_to_clinical_nodes(driver)
        
        # Connect WHO/CDC guideline references to all clinical nodes
        connect_who_cdc_references(driver)
        
        # Update API schema for references
        update_api_for_references(driver)
        
        # Close the Neo4j connection
        driver.close()
        logging.info("Neo4j driver closed")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
