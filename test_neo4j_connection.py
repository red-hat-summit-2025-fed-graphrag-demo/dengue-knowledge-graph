#!/usr/bin/env python3
"""
Neo4j Connection Test Script for Dengue Knowledge Graph
Tests connectivity to the Neo4j database and runs basic queries.
"""
from neo4j import GraphDatabase, basic_auth
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Neo4j connection details
NEO4J_URI = "bolt://neo4j-dengue-service.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "denguePassw0rd!"

def test_neo4j_connection():
    """Test connection to Neo4j database and run basic queries"""
    try:
        logger.info(f"Attempting to connect to Neo4j at {NEO4J_URI}")
        
        # Create driver with basic authentication
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
        )
        
        # Test the connection with simple queries
        with driver.session() as session:
            # Verify connection with simple query
            test_result = session.run("RETURN 1 AS n").single()
            if test_result and test_result.get("n") == 1:
                logger.info("Basic connectivity test successful")
            
            # Get database labels to verify schema
            result = session.run("CALL db.labels()")
            labels = [record["label"] for record in result]
            
            logger.info("Successfully connected to Neo4j database!")
            logger.info(f"Node labels in database: {labels}")
            
            # Get a count of nodes by label
            if labels:
                logger.info("Node counts by label:")
                for label in labels:
                    count_query = f"MATCH (n:{label}) RETURN count(n) AS count"
                    count_result = session.run(count_query).single()
                    if count_result:
                        logger.info(f"  {label}: {count_result['count']} nodes")
            
            # Get relationship types
            rel_types_result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in rel_types_result]
            logger.info(f"Relationship types in database: {rel_types}")
            
            # Run a more complex query if there are nodes in the database
            if labels:
                # Sample the first few nodes of each type
                logger.info("Sample nodes by label:")
                for label in labels[:3]:  # Limit to first 3 labels to avoid too much output
                    sample_query = f"""
                    MATCH (n:{label})
                    RETURN n LIMIT 2
                    """
                    sample_result = session.run(sample_query)
                    records = [dict(record["n"].items()) for record in sample_result]
                    if records:
                        logger.info(f"  {label} samples: {records}")
        
        # Close the driver connection
        driver.close()
        logger.info("Connection test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        return False

if __name__ == "__main__":
    success = test_neo4j_connection()
    sys.exit(0 if success else 1)
