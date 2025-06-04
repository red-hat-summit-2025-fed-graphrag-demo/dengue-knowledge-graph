"""
Neo4j Database Interface Module
Handles database connection and query execution for the Dengue Knowledge Graph API
"""
import os
from typing import Dict, List, Any, Optional, Generator
import logging
from neo4j import GraphDatabase, Session, Driver, basic_auth

# Configure logging
logger = logging.getLogger(__name__)

# Get connection details from environment variables
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")


def get_neo4j_driver() -> Driver:
    """Get a Neo4j driver instance
    
    Returns:
        Neo4j driver object
    """
    logger.info(f"Creating Neo4j driver for {NEO4J_URI}")
    
    try:
        # Create driver with all the security settings needed for development
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_lifetime=1000  # Shorter connection lifetime for development
        )
        
        # Test the connection with a simple query that doesn't require auth
        with driver.session() as session:
            try:
                # Simple connectivity check
                result = session.run("RETURN 1 AS n")
                value = result.single()[0]
                logger.info(f"Successfully connected to Neo4j: {value}")
            except Exception as e:
                logger.warning(f"Test query failed, but connection may still be usable: {str(e)}")
        
        logger.info("Neo4j driver created successfully")
        return driver
        
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise


class Neo4jDatabase:
    """Neo4j database connection and query executor"""

    def __init__(self):
        """Initialize database interface"""
        self.driver = None
        self.connect()

    def connect(self, retries: int = 5, retry_interval: int = 5) -> None:
        """Establish connection to Neo4j database with retry logic
        
        Args:
            retries: Number of connection attempts
            retry_interval: Seconds between retries
        """
        attempts = 0
        last_error = None
        
        while attempts < retries:
            try:
                logger.info(f"Connecting to Neo4j at {NEO4J_URI} (attempt {attempts+1}/{retries})")
                
                # Use the global driver function to maintain consistency
                self.driver = get_neo4j_driver()
                return
            
            except Exception as e:
                last_error = e
                logger.warning(f"Connection attempt {attempts+1} failed: {e}")
                attempts += 1
                if attempts < retries:
                    import time
                    time.sleep(retry_interval)
        
        # If we get here, we failed to connect
        logger.error(f"Failed to connect to Neo4j after {retries} attempts")
        raise ConnectionError(f"Could not connect to Neo4j database: {last_error}")

    def get_session(self) -> Session:
        """Get a Neo4j session
        
        Returns:
            Neo4j session object
        """
        if not self.driver:
            self.connect()
        return self.driver.session()

    def close(self) -> None:
        """Close the database connection"""
        if self.driver:
            self.driver.close()
            self.driver = None
            
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if parameters is None:
            parameters = {}
            
        with self.get_session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]
    
    def execute_write_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a write query and return summary
        
        Args:
            query: Cypher query string for writing data
            parameters: Query parameters
            
        Returns:
            Query summary with counters
        """
        if parameters is None:
            parameters = {}
            
        with self.get_session() as session:
            result = session.run(query, parameters)
            summary = result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set
            }


# Singleton database instance
def get_db() -> Generator[Driver, None, None]:
    """Database dependency for FastAPI"""
    db = Neo4jDatabase()
    try:
        yield db.driver
    finally:
        db.close()
