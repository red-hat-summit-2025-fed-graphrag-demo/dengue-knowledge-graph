"""
Dengue Knowledge Graph - Neo4j Schema Loader

This script initializes the Neo4j database with the proper schema
and constraints for the Dengue Knowledge Graph.
"""
import os
import logging
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database import get_neo4j_driver
from neo4j.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define Neo4j constraints and indexes
CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Location) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:DengueCase) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Vector) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:RiskFactor) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Prevention) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Treatment) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Symptom) REQUIRE n.name IS UNIQUE",
]

# Define schema for the Dengue Knowledge Graph
SCHEMA_CYPHER = """
// Create basic schema for dengue cases and related entities
MERGE (v:Vector {name: 'Aedes aegypti'})
MERGE (v2:Vector {name: 'Aedes albopictus'})

// Create symptoms
MERGE (s1:Symptom {name: 'Fever'})
MERGE (s2:Symptom {name: 'Headache'})
MERGE (s3:Symptom {name: 'Joint pain'})
MERGE (s4:Symptom {name: 'Muscle pain'})
MERGE (s5:Symptom {name: 'Rash'})
MERGE (s6:Symptom {name: 'Bleeding'})
MERGE (s7:Symptom {name: 'Low platelet count'})
MERGE (s8:Symptom {name: 'Nausea'})
MERGE (s9:Symptom {name: 'Vomiting'})

// Create risk factors
MERGE (r1:RiskFactor {name: 'Previous dengue infection'})
MERGE (r2:RiskFactor {name: 'Tropical climate'})
MERGE (r3:RiskFactor {name: 'Poor sanitation'})
MERGE (r4:RiskFactor {name: 'Standing water'})
MERGE (r5:RiskFactor {name: 'Urban environment'})

// Create prevention methods
MERGE (p1:Prevention {name: 'Mosquito nets'})
MERGE (p2:Prevention {name: 'Insect repellent'})
MERGE (p3:Prevention {name: 'Eliminating standing water'})
MERGE (p4:Prevention {name: 'Window screens'})
MERGE (p5:Prevention {name: 'Vaccination'})

// Create treatments
MERGE (t1:Treatment {name: 'Pain relievers'})
MERGE (t2:Treatment {name: 'Fluid replacement'})
MERGE (t3:Treatment {name: 'Rest'})
MERGE (t4:Treatment {name: 'Hospitalization'})

// Create relationships between entities
MATCH (v:Vector {name: 'Aedes aegypti'})
MATCH (s:Symptom)
CREATE (v)-[:CAUSES]->(s)

MATCH (v:Vector {name: 'Aedes albopictus'})
MATCH (s:Symptom)
CREATE (v)-[:CAUSES]->(s)

MATCH (r:RiskFactor)
MATCH (v:Vector)
CREATE (r)-[:INCREASES_RISK_OF]->(v)

MATCH (p:Prevention)
MATCH (v:Vector)
CREATE (p)-[:PREVENTS]->(v)

MATCH (s:Symptom)
MATCH (t:Treatment)
CREATE (s)-[:TREATED_BY]->(t)
"""

def create_constraints_and_indexes(driver):
    """Create all necessary constraints and indexes in Neo4j"""
    with driver.session() as session:
        for constraint in CONSTRAINTS:
            try:
                logger.info(f"Creating constraint: {constraint}")
                session.run(constraint)
            except ClientError as e:
                # If constraint already exists or similar error
                logger.warning(f"Error creating constraint: {e}")

def load_schema(driver):
    """Load the basic schema into Neo4j"""
    with driver.session() as session:
        logger.info("Creating basic schema...")
        session.run(SCHEMA_CYPHER)
        logger.info("Schema created successfully")

def main():
    """Main function to initialize the Neo4j database"""
    logger.info("Connecting to Neo4j database...")
    driver = get_neo4j_driver()
    
    try:
        # Create constraints and indexes
        create_constraints_and_indexes(driver)
        
        # Load the schema
        load_schema(driver)
        
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        driver.close()

if __name__ == "__main__":
    main()
