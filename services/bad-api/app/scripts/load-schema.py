import os
from neo4j import GraphDatabase, basic_auth
import logging
import time
import json
import re
import sys
from pathlib import Path
try:
    import owlready2
except ImportError:
    logging.warning("owlready2 not found, OWL loading will not be available")
    owlready2 = None

# Configure logging with more details for debugging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
# Get connection details from environment variables or use defaults
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j-dengue:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")
NEO4J_AUTH = os.environ.get("NEO4J_AUTH", "none")  # Set to 'none' to disable auth, matches deployment

# Print configs for debugging
logging.info(f"Using Neo4j connection: {NEO4J_URI} with auth type: {NEO4J_AUTH}")
logging.info(f"Current working directory: {os.getcwd()}")

# Define base path assuming script is in /app/scripts/
SCRIPT_DIR = Path(__file__).parent
CYPHER_DIR = SCRIPT_DIR.parent / 'cypher'
DATA_DIR = SCRIPT_DIR.parent / 'data'

logging.info(f"Looking for Cypher files in: {CYPHER_DIR}")
logging.info(f"Looking for Data files in: {DATA_DIR}")

SCHEMA_FILES = {
    'constraints': CYPHER_DIR / 'dengue-schema.cypher',
    'nodes': CYPHER_DIR / 'dengue-nodes.cypher',
    'relationships': CYPHER_DIR / 'dengue-relationships.cypher'
}

# Paths to data files
DATA_FILES = {
    'snomed': DATA_DIR / 'dengue-snomed.json',
    'obo': DATA_DIR / 'dengue-ontology.obo',
    'owl': DATA_DIR / 'idoden_beta0.15b.owl'
}

def read_cypher_file(filepath):
    """Read a Cypher file and return a list of statements."""
    if not filepath.exists():
        logging.error(f"File not found: {filepath}")
        return []
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Split by semicolons, but only when not inside quotes
    statements = []
    current_statement = ""
    in_quote = False
    for char in content:
        if char == '"' or char == "'":
            in_quote = not in_quote
        
        current_statement += char
        
        if char == ';' and not in_quote:
            statements.append(current_statement.strip())
            current_statement = ""
    
    # Filter out comments and empty statements
    filtered_statements = []
    for stmt in statements:
        # Remove line comments
        lines = [line for line in stmt.split('\n') if not line.strip().startswith('//')]
        clean_stmt = '\n'.join(lines).strip()
        if clean_stmt and not clean_stmt == ';':
            filtered_statements.append(clean_stmt)
    
    return filtered_statements

def run_cypher_statements(driver, statements, description):
    """Executes a list of Cypher statements within a session."""
    with driver.session() as session:
        for i, statement in enumerate(statements):
            logging.info(f"Running {description} statement {i+1}/{len(statements)}: {statement[:100]}...")
            try:
                session.run(statement)
            except Exception as e:
                logging.error(f"Error executing statement: {statement}\n{e}")
                # Continue executing remaining statements
                # Uncomment to stop on first error: raise

def load_snomed_data(driver, filepath):
    """Load SNOMED CT data from JSON file."""
    if not filepath.exists():
        logging.warning(f"SNOMED CT file not found: {filepath}")
        return
    
    logging.info(f"Loading SNOMED CT data from {filepath}...")
    
    try:
        with open(filepath, 'r') as f:
            snomed_data = json.load(f)
        
        # Process SNOMED concepts
        statements = []
        
        # Create SNOMED concept nodes
        for concept in snomed_data.get("concepts", []):
            term = concept["term"].replace("'", "\\'")  # Use SQL-style quote escaping
            stmt = f"""
            MERGE (c:SnomedConcept {{sctid: '{concept["id"]}'}})
            ON CREATE SET 
                c.term = '{term}',
                c.conceptType = '{concept.get("conceptType", "")}'
            """
            statements.append(stmt)
            
            # Connect to Disease nodes if possible
            if 'dengue' in concept["term"].lower():
                first_word = concept["term"].split()[0]
                stmt = f"""
                MATCH (c:SnomedConcept {{sctid: '{concept["id"]}'}})
                MATCH (d:Disease)
                WHERE toLower(d.name) CONTAINS toLower('{first_word}')
                MERGE (d)-[:HAS_SNOMED_CONCEPT]->(c)
                """
                statements.append(stmt)
        
        # Process relationships
        for rel in snomed_data.get("relationships", []):
            rel_type = rel["type"].replace(' ', '_')
            stmt = f"""
            MATCH (source:SnomedConcept {{sctid: '{rel["source"]}'}})
            MATCH (target:SnomedConcept {{sctid: '{rel["target"]}'}})
            MERGE (source)-[:{rel_type}]->(target)
            """
            statements.append(stmt)
        
        run_cypher_statements(driver, statements, "SNOMED CT data loading")
        logging.info("Successfully loaded SNOMED CT data")
    
    except Exception as e:
        logging.error(f"Error loading SNOMED CT data: {e}")

def load_obo_data(driver, filepath):
    """Load data from OBO ontology file."""
    if not filepath.exists():
        logging.warning(f"OBO file not found: {filepath}")
        return
    
    logging.info(f"Loading OBO data from {filepath}...")
    
    try:
        # Basic OBO parser (minimal implementation)
        term_pattern = r'\[Term\](.*?)(?=\[|\Z)'
        id_pattern = r'id:\s*(.*)'
        name_pattern = r'name:\s*(.*)'
        is_a_pattern = r'is_a:\s*(.*?)\s*(?:!.*)?$'
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        terms = re.findall(term_pattern, content, re.DOTALL)
        statements = []
        
        for term in terms:
            term_id = re.search(id_pattern, term)
            name = re.search(name_pattern, term)
            
            if term_id and name:
                term_id = term_id.group(1).strip()
                name = name.group(1).strip().replace("'", "\\'")  # SQL-style quote escaping
                
                # Create OntologyTerm node
                stmt = f"""
                MERGE (ot:OntologyTerm {{id: '{term_id}'}})
                ON CREATE SET ot.name = '{name}', ot.source = 'OBO'
                """
                statements.append(stmt)
                
                # Process is_a relationships
                is_a_rels = re.findall(is_a_pattern, term, re.MULTILINE)
                for is_a in is_a_rels:
                    parent_id = is_a.strip()
                    stmt = f"""
                    MATCH (child:OntologyTerm {{id: '{term_id}'}})
                    MATCH (parent:OntologyTerm {{id: '{parent_id}'}})
                    MERGE (child)-[:IS_A]->(parent)
                    """
                    statements.append(stmt)
                
                # Create relationship to Disease if term relates to dengue
                if 'dengue' in name.lower():
                    stmt = f"""
                    MATCH (ot:OntologyTerm {{id: '{term_id}'}})
                    MATCH (d:Disease)
                    WHERE toLower(d.name) CONTAINS 'dengue'
                    MERGE (d)-[:HAS_ONTOLOGY_TERM]->(ot)
                    """
                    statements.append(stmt)
        
        run_cypher_statements(driver, statements, "OBO data loading")
        logging.info("Successfully loaded OBO data")
    
    except Exception as e:
        logging.error(f"Error loading OBO data: {e}")

def load_owl_data(driver, filepath):
    """Load data from OWL ontology file."""
    if not filepath.exists():
        logging.warning(f"OWL file not found: {filepath}")
        return
    
    if owlready2 is None:
        logging.error("Cannot load OWL file without owlready2 library. Please install: pip install owlready2")
        return
    
    logging.info(f"Loading OWL data from {filepath}...")
    
    try:
        # Load the ontology
        onto = owlready2.get_ontology(f"file://{str(filepath.resolve())}").load()
        
        # Process classes
        statements = []
        processed_classes = set()
        
        # Create OntologyTerm nodes for dengue-related classes
        for cls in onto.classes():
            class_name = cls.label.first() if len(cls.label) > 0 else cls.name
            
            # Skip if already processed
            if cls.iri in processed_classes:
                continue
            
            processed_classes.add(cls.iri)
            
            # Only process dengue-related classes
            if 'dengue' in str(class_name).lower():
                # Create node statement
                class_id = cls.name if hasattr(cls, 'name') else cls.iri.split('/')[-1]
                safe_class_name = str(class_name).replace("'", "''")
                stmt = f"""
                MERGE (ot:OntologyTerm {{id: '{class_id}'}})
                ON CREATE SET 
                    ot.name = '{safe_class_name}',
                    ot.source = 'OWL',
                    ot.iri = '{cls.iri}'
                """
                statements.append(stmt)
                
                # Process subclass relationships
                for parent in cls.is_a:
                    if isinstance(parent, owlready2.entity.ThingClass):
                        parent_name = parent.label.first() if len(parent.label) > 0 else parent.name
                        parent_id = parent.name if hasattr(parent, 'name') else parent.iri.split('/')[-1]
                        
                        # Skip if parent is a restriction or other non-class entity
                        if parent_id and parent_name:
                            safe_parent_name = str(parent_name).replace("'", "''")
                            stmt = f"""
                            MERGE (child:OntologyTerm {{id: '{class_id}'}})
                            MERGE (parent:OntologyTerm {{id: '{parent_id}'}})
                            ON CREATE SET parent.name = '{safe_parent_name}'
                            MERGE (child)-[:IS_A]->(parent)
                            """
                            statements.append(stmt)
                
                # Connect to Disease if term relates to dengue
                if 'dengue' in str(class_name).lower():
                    stmt = f"""
                    MATCH (ot:OntologyTerm {{id: '{class_id}'}})
                    MATCH (d:Disease)
                    WHERE toLower(d.name) CONTAINS 'dengue'
                    MERGE (d)-[:HAS_ONTOLOGY_TERM]->(ot)
                    """
                    statements.append(stmt)
        
        # Execute the statements
        run_cypher_statements(driver, statements, "OWL data loading")
        logging.info(f"Successfully loaded {len(processed_classes)} OWL classes")
    
    except Exception as e:
        logging.error(f"Error loading OWL data: {e}")

def load_schema(driver):
    """Load the core schema from Cypher files."""
    # Load constraints
    constraints_file = SCHEMA_FILES['constraints']
    if constraints_file.exists():
        constraints = read_cypher_file(constraints_file)
        run_cypher_statements(driver, constraints, "constraint")
    else:
        logging.warning(f"Constraints file not found: {constraints_file}")
    
    # Load nodes
    nodes_file = SCHEMA_FILES['nodes']
    if nodes_file.exists():
        nodes = read_cypher_file(nodes_file)
        run_cypher_statements(driver, nodes, "node creation")
    else:
        logging.warning(f"Nodes file not found: {nodes_file}")
    
    # Load relationships
    relationships_file = SCHEMA_FILES['relationships']
    if relationships_file.exists():
        relationships = read_cypher_file(relationships_file)
        run_cypher_statements(driver, relationships, "relationship creation")
    else:
        logging.warning(f"Relationships file not found: {relationships_file}")

def create_region_and_prediction_data(driver):
    """Create sample geographical regions and prediction data nodes for demonstration."""
    statements = [
        # Regions for scenario queries
        """
        MERGE (r1:Region {id: 'R:1', name: 'Miami-Dade'})
        ON CREATE SET r1.country = 'United States', 
                      r1.region_type = 'County',
                      r1.population = 2716940,
                      r1.area_km2 = 5040;
        """,
        """
        MERGE (r2:Region {id: 'R:2', name: 'New Mexico'})
        ON CREATE SET r2.country = 'United States', 
                      r2.region_type = 'State',
                      r2.population = 2096640,
                      r2.area_km2 = 315194;
        """,
        """
        MERGE (r3:Region {id: 'R:3', name: 'Phuket'})
        ON CREATE SET r3.country = 'Thailand', 
                      r3.region_type = 'Province',
                      r3.population = 416582,
                      r3.area_km2 = 576,
                      r3.current_transmission_level = 'High',
                      r3.seasonal_risk_pattern = 'Peaks June-October';
        """,
        """
        MERGE (r4:Region {id: 'R:4', name: 'Houston'})
        ON CREATE SET r4.country = 'United States', 
                      r4.region_type = 'City',
                      r4.population = 2304580,
                      r4.area_km2 = 1651;
        """,
        """
        MERGE (r5:Region {id: 'R:5', name: 'Puerto Rico'})
        ON CREATE SET r5.country = 'United States', 
                      r5.region_type = 'Territory',
                      r5.population = 3285874,
                      r5.area_km2 = 9104;
        """,
        
        # Connect regions to disease
        """
        MATCH (r:Region {name: 'Phuket'})
        MATCH (d:Disease {name: 'Dengue Fever'})
        MERGE (r)-[:HAS_ENDEMIC_DISEASE]->(d);
        """,
        
        # Climate factors for regions
        """
        MERGE (cf1:ClimateFactor {id: 'CF:1', name: 'High Temperature'}) 
        ON CREATE SET cf1.impact_level = 'High',
                      cf1.description = 'Average temperature above 30°C increases mosquito development rate';
        """,
        """
        MERGE (cf2:ClimateFactor {id: 'CF:2', name: 'High Humidity'}) 
        ON CREATE SET cf2.impact_level = 'High',
                      cf2.description = 'Relative humidity >70% extends mosquito lifespan';
        """,
        """
        MERGE (cf3:ClimateFactor {id: 'CF:3', name: 'Heavy Rainfall'}) 
        ON CREATE SET cf3.impact_level = 'Medium',
                      cf3.description = 'Creates breeding sites but may flush out larvae if excessive';
        """,
        
        # Connect climate factors to regions
        """
        MATCH (r:Region {name: 'Miami-Dade'})
        MATCH (cf:ClimateFactor) 
        MERGE (r)-[:HAS_CLIMATE_FACTOR]->(cf);
        """,
        
        # Create sample historical data
        """
        MATCH (r:Region {name: 'Miami-Dade'})
        UNWIND [
          {id: 'HD:1', year: 2020, month: 1, case_count: 12},
          {id: 'HD:2', year: 2020, month: 2, case_count: 15},
          {id: 'HD:3', year: 2020, month: 3, case_count: 18},
          {id: 'HD:4', year: 2020, month: 4, case_count: 24},
          {id: 'HD:5', year: 2021, month: 1, case_count: 14},
          {id: 'HD:6', year: 2021, month: 2, case_count: 19},
          {id: 'HD:7', year: 2021, month: 3, case_count: 25},
          {id: 'HD:8', year: 2021, month: 4, case_count: 32}
        ] AS data
        MERGE (h:HistoricalData {id: data.id})
        ON CREATE SET h.year = data.year,
                      h.month = data.month,
                      h.case_count = data.case_count
        MERGE (r)-[:HAS_HISTORICAL_DATA]->(h);
        """,
        
        # Sample prediction data
        """
        MATCH (r:Region {name: 'Houston'})
        UNWIND [
          {id: 'PD:1', prediction_date: date('2025-05-15'), predicted_cases: 18, confidence_interval: '12-24'},
          {id: 'PD:2', prediction_date: date('2025-06-15'), predicted_cases: 27, confidence_interval: '18-36'},
          {id: 'PD:3', prediction_date: date('2025-07-15'), predicted_cases: 42, confidence_interval: '30-54'}
        ] AS data
        MERGE (pd:PredictionData {id: data.id})
        ON CREATE SET pd.prediction_date = data.prediction_date,
                      pd.predicted_cases = data.predicted_cases,
                      pd.confidence_interval = data.confidence_interval
        MERGE (r)-[:HAS_PREDICTION_DATA]->(pd);
        """
    ]
    
    run_cypher_statements(driver, statements, "region and prediction data creation")

def create_prevention_and_recommendation_data(driver):
    """Create prevention measures, recommendations and vector control data."""
    statements = [
        # Prevention measures
        """
        MERGE (pm1:PreventionMeasure {id: 'PM:1', name: 'Insect Repellent Use'})
        ON CREATE SET pm1.effectiveness_level = 'High',
                      pm1.traveler_relevant = true,
                      pm1.implementation_details = 'Use EPA-registered insect repellents containing DEET, picaridin, IR3535, oil of lemon eucalyptus, para-menthane-diol, or 2-undecanone';
        """,
        """
        MERGE (pm2:PreventionMeasure {id: 'PM:2', name: 'Protective Clothing'})
        ON CREATE SET pm2.effectiveness_level = 'Medium',
                      pm2.traveler_relevant = true,
                      pm2.implementation_details = 'Wear long-sleeved shirts and long pants, especially during dawn and dusk';
        """,
        """
        MERGE (pm3:PreventionMeasure {id: 'PM:3', name: 'Bed Nets'})
        ON CREATE SET pm3.effectiveness_level = 'High',
                      pm3.traveler_relevant = true,
                      pm3.implementation_details = 'Use permethrin-treated bed nets, especially in areas without air conditioning or screened windows';
        """,
        
        # Connect prevention to disease
        """
        MATCH (pm:PreventionMeasure)
        MATCH (d:Disease {name: 'Dengue Fever'})
        MERGE (pm)-[:PREVENTS]->(d);
        """,
        
        # Vector control
        """
        MERGE (vc1:VectorControl {id: 'VC:1', name: 'Source Reduction'})
        ON CREATE SET vc1.threshold_criteria = 'Any mosquito breeding sites identified',
                      vc1.implementation_steps = '1. Remove standing water sources, 2. Clean and cover containers, 3. Fill tree holes, 4. Maintain drains';
        """,
        """
        MERGE (vc2:VectorControl {id: 'VC:2', name: 'Enhanced Surveillance'})
        ON CREATE SET vc2.threshold_criteria = '>5 dengue cases within a 3-week period in a specific area',
                      vc2.implementation_steps = '1. Deploy ovitraps, 2. Increase adult mosquito trapping, 3. Monitor insecticide resistance, 4. Conduct rapid case investigation';
        """,
        """
        MERGE (vc3:VectorControl {id: 'VC:3', name: 'Larviciding'})
        ON CREATE SET vc3.threshold_criteria = 'Larval indices above threshold (House Index >5%, Container Index >10%)',
                      vc3.implementation_steps = '1. Apply appropriate larvicides to breeding sites, 2. Focus on containers that cannot be emptied, 3. Use biological control where appropriate';
        """,
        """
        MERGE (vc4:VectorControl {id: 'VC:4', name: 'Adult Mosquito Control'})
        ON CREATE SET vc4.threshold_criteria = 'Confirmed dengue outbreak OR adult indices above threshold',
                      vc4.implementation_steps = '1. Conduct thermal fogging or ULV spraying, 2. Target areas around index cases, 3. Apply during peak vector activity, 4. Rotate insecticides to prevent resistance';
        """,
        
        # Organization nodes
        """
        MERGE (org1:Organization {id: 'ORG:1', name: 'World Health Organization'})
        ON CREATE SET org1.abbreviation = 'WHO',
                      org1.url = 'https://www.who.int',
                      org1.role = 'International Health Agency';
        """,
        """
        MERGE (org2:Organization {id: 'ORG:2', name: 'Centers for Disease Control and Prevention'})
        ON CREATE SET org2.abbreviation = 'CDC',
                      org2.url = 'https://www.cdc.gov',
                      org2.role = 'National Health Agency';
        """,
        
        # Connect organizations to vector control
        """
        MATCH (org:Organization)
        MATCH (vc:VectorControl)
        MERGE (org)-[:PROVIDES_GUIDANCE_ON]->(vc);
        """
    ]
    
    run_cypher_statements(driver, statements, "prevention and recommendation data creation")

def create_treatment_protocol_data(driver):
    """Create treatment protocols and recommendations."""
    statements = [
        # Treatment protocols
        """
        MERGE (tp1:TreatmentProtocol {id: 'TP:1', name: 'Oral Fluid Management'})
        ON CREATE SET tp1.description = 'Encourage oral fluids containing water, ORS, fruit juice and other liquids containing electrolytes. Monitor oral intake and urine output.',
                      tp1.evidence_level = 'Strong';
        """,
        """
        MERGE (tp2:TreatmentProtocol {id: 'TP:2', name: 'Group B IV Fluid Protocol'})
        ON CREATE SET tp2.description = 'Begin with isotonic solutions such as 0.9% saline at maintenance rate. Reassess clinical status and adjust rate accordingly.',
                      tp2.evidence_level = 'Strong';
        """,
        """
        MERGE (tp3:TreatmentProtocol {id: 'TP:3', name: 'Shock Fluid Resuscitation'})
        ON CREATE SET tp3.description = 'Begin with 5-10 ml/kg/hour of crystalloid solution, reassess after 1 hour. If improving, reduce rate gradually. If not improving, give another 10-20 ml/kg bolus.',
                      tp3.evidence_level = 'Strong';
        """,
        """
        MERGE (tp4:TreatmentProtocol {id: 'TP:4', name: 'Platelet Transfusion Protocol'})
        ON CREATE SET tp4.description = 'Consider platelet transfusion in severe thrombocytopenia (<10,000/mm³) with significant bleeding. Not recommended prophylactically.',
                      tp4.evidence_level = 'Conditional';
        """,
        
        # Connect protocols to clinical classifications
        """
        MATCH (tp:TreatmentProtocol {name: 'Oral Fluid Management'})
        MATCH (c:ClinicalClassification {name: 'Dengue without Warning Signs'})
        MERGE (c)-[:REQUIRES_TREATMENT]->(tp);
        """,
        """
        MATCH (tp:TreatmentProtocol {name: 'Group B IV Fluid Protocol'})
        MATCH (c:ClinicalClassification {name: 'Dengue with Warning Signs'})
        MERGE (c)-[:REQUIRES_TREATMENT]->(tp);
        """,
        """
        MATCH (tp:TreatmentProtocol {name: 'Shock Fluid Resuscitation'})
        MATCH (c:ClinicalClassification {name: 'Severe Dengue'})
        MERGE (c)-[:REQUIRES_TREATMENT]->(tp);
        """,
        """
        MATCH (tp:TreatmentProtocol {name: 'Platelet Transfusion Protocol'})
        MATCH (c:ClinicalClassification {name: 'Severe Dengue'})
        MERGE (c)-[:REQUIRES_TREATMENT]->(tp);
        """,
        
        # Connect warning signs to specific treatments
        """
        MATCH (ws:WarningSign)
        WHERE ws.name IN ['Persistent Vomiting', 'Abdominal Pain or Tenderness']
        MATCH (tp:TreatmentProtocol {name: 'Group B IV Fluid Protocol'})
        MERGE (ws)-[:REQUIRES_SPECIFIC]->(tp);
        """
    ]
    
    run_cypher_statements(driver, statements, "treatment protocol data creation")

def create_risk_factor_data(driver):
    """Create risk factor data for serotype-specific scenarios."""
    statements = [
        # Risk factors
        """
        MERGE (rf1:RiskFactor {id: 'RF:1', name: 'Prior DENV Infection (Different Serotype)'})
        ON CREATE SET rf1.description = 'Prior infection with one dengue serotype increases risk of severe disease when infected with a different serotype',
                      rf1.mechanism = 'Antibody-dependent enhancement (ADE)';
        """,
        
        # Connect risk factors
        """
        MATCH (rf:RiskFactor {name: 'Prior DENV Infection (Different Serotype)'})
        MATCH (sd:Disease {name: 'Severe Dengue'})
        MERGE (rf)-[:INCREASES_RISK_OF]->(sd);
        """,
        
        # Management recommendations
        """
        MERGE (r1:Recommendation {id: 'REC:1', name: 'Enhanced Monitoring for Secondary Infections'})
        ON CREATE SET r1.description = 'Patients with confirmed prior dengue infection should be monitored more closely with daily complete blood counts and clinical assessments during acute illness',
                      r1.evidence_level = 'Strong';
        """,
        """
        MERGE (r2:Recommendation {id: 'REC:2', name: 'Lower Threshold for Hospitalization'})
        ON CREATE SET r2.description = 'Consider earlier hospitalization for patients with confirmed prior dengue infection, especially if infected with a different serotype',
                      r2.evidence_level = 'Conditional';
        """,
        
        # Connect recommendations to risk factors
        """
        MATCH (rf:RiskFactor {name: 'Prior DENV Infection (Different Serotype)'})
        MATCH (r:Recommendation)
        MERGE (rf)-[:HAS_MANAGEMENT_RECOMMENDATION]->(r);
        """
    ]
    
    run_cypher_statements(driver, statements, "risk factor data creation")

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
                logging.error("Could not connect to Neo4j after multiple retries. Exiting.")
                if driver:
                    driver.close()
                return None
    
    return None

def main():
    """Main function to connect to Neo4j and load schema and data."""
    driver = connect_to_neo4j()
    
    if not driver:
        return
    
    try:
        # Step 1: Load the core schema
        load_schema(driver)
        
        # Step 2: Load sample data for demonstration
        create_region_and_prediction_data(driver)
        create_prevention_and_recommendation_data(driver)
        create_treatment_protocol_data(driver)
        create_risk_factor_data(driver)
        
        # Step 3: Load ontology data (if requested)
        load_snomed_data(driver, DATA_FILES['snomed'])
        load_obo_data(driver, DATA_FILES['obo'])
        load_owl_data(driver, DATA_FILES['owl'])
        
        logging.info("Successfully loaded schema and sample data.")
    
    except Exception as e:
        logging.error(f"Error during data loading: {e}")
    
    finally:
        # Close the driver connection
        if driver:
            driver.close()
            logging.info("Neo4j driver closed.")

if __name__ == "__main__":
    main()
