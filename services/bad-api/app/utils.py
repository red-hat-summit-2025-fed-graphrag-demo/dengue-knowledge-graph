import sys
from loguru import logger
from neo4j import GraphDatabase, Driver
from .config import settings # Use relative import within the same package
from .models import SampleQuery # Import necessary model
import uuid
from typing import Dict, Any

def setup_logging():
    """Configure Loguru logger."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    logger.info(f"Logging configured with level: {settings.LOG_LEVEL}")


_neo4j_driver: Driver | None = None

def get_neo4j_driver() -> Driver:
    """Get or initialize the Neo4j driver instance."""
    global _neo4j_driver
    if _neo4j_driver is None:
        logger.info(f"Initializing Neo4j driver for URI: {settings.NEO4J_URI}")
        try:
            _neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                # Add other driver config if needed, e.g., encrypted=True
            )
            # Verify connection
            _neo4j_driver.verify_connectivity()
            logger.info("Neo4j driver initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            # Re-raise the exception to prevent the app from starting with a bad driver
            raise
    return _neo4j_driver

def close_neo4j_driver():
    """Close the Neo4j driver connection if it exists."""
    global _neo4j_driver
    if _neo4j_driver is not None:
        logger.info("Closing Neo4j driver connection.")
        _neo4j_driver.close()
        _neo4j_driver = None
        logger.info("Neo4j driver closed.")


def generate_sample_nodes(driver: Driver, sample_query: SampleQuery) -> Dict[str, Any]:
    """Generate sample nodes and relationships in the graph."""
    created_nodes = []
    created_relationships = []
    node_ids = []

    try:
        with driver.session() as session:
            # Create nodes
            logger.info(f"Creating {sample_query.num_nodes} sample nodes with label '{sample_query.node_label}'")
            for i in range(sample_query.num_nodes):
                node_id = str(uuid.uuid4())
                node_properties = {'name': f'Sample_{sample_query.node_label}_{i+1}', 'uuid': node_id}
                result = session.run(
                    f"CREATE (n:{sample_query.node_label} $props) RETURN elementId(n) as id",
                    props=node_properties
                )
                record = result.single()
                if record:
                    created_nodes.append(record['id'])
                    node_ids.append(record['id']) # Store node IDs for relationship creation
            logger.info(f"Created {len(created_nodes)} nodes.")

            # Create relationships (if specified and possible)
            if sample_query.relationship_type and sample_query.num_relationships > 0 and len(node_ids) >= 2:
                logger.info(f"Creating {sample_query.num_relationships} sample relationships of type '{sample_query.relationship_type}'")
                import random
                rel_count = 0
                # Attempt to create specified number of unique relationships
                max_attempts = sample_query.num_relationships * 5 # Avoid infinite loops
                attempts = 0
                while rel_count < sample_query.num_relationships and attempts < max_attempts:
                    attempts += 1
                    start_node_id = random.choice(node_ids)
                    end_node_id = random.choice(node_ids)
                    if start_node_id == end_node_id: # Avoid self-loops for simplicity
                        continue

                    rel_props = {'description': f'Sample relationship {rel_count+1}'}
                    result = session.run(
                        f"MATCH (a), (b) WHERE elementId(a) = $start_id AND elementId(b) = $end_id "
                        f"CREATE (a)-[r:{sample_query.relationship_type} $props]->(b) RETURN elementId(r) as id",
                        start_id=start_node_id, end_id=end_node_id, props=rel_props
                    )
                    record = result.single()
                    if record:
                        created_relationships.append(record['id'])
                        rel_count += 1
                logger.info(f"Created {len(created_relationships)} relationships.")
            elif sample_query.num_relationships > 0:
                 logger.warning("Cannot create relationships: Need at least 2 nodes or relationship_type not specified.")

        return {
            "message": "Sample data generation complete.",
            "nodes_created": len(created_nodes),
            "relationships_created": len(created_relationships)
        }
    except Exception as e:
        logger.error(f"Error generating sample data: {e}")
        # Consider raising the exception or returning a more detailed error structure
        return {"error": f"Failed to generate sample data: {e}"}
