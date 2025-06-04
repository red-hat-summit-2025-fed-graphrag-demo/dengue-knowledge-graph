#!/usr/bin/env python3
"""
Neo4j connection test script for OpenShift passthrough route
"""
from neo4j import GraphDatabase, basic_auth
import sys

# Neo4j connection details via passthrough route
NEO4J_URI = "bolt+s://neo4j-bolt-neo4j-dengue-service.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com:443"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "denguePassw0rd!"

print(f"Attempting to connect to Neo4j at {NEO4J_URI}")
print(f"Using credentials: {NEO4J_USER}/{'*' * len(NEO4J_PASSWORD)}")

try:
    # Create driver with basic authentication
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
    )
    
    # Test the connection with a simple query
    with driver.session() as session:
        print("Connection established, running test query...")
        result = session.run("RETURN 1 AS n").single()
        if result and result.get("n") == 1:
            print("Query executed successfully!")
            
            # Get database labels to verify schema access
            print("\nFetching database schema information...")
            labels_result = session.run("CALL db.labels()")
            labels = [record["label"] for record in labels_result]
            print(f"Node labels in database: {labels}")
            
            # Get a count of nodes
            if labels:
                print("\nCounting nodes by label:")
                for label in labels[:5]:  # Limit to first 5 labels
                    count_query = f"MATCH (n:{label}) RETURN count(n) AS count"
                    count_result = session.run(count_query).single()
                    if count_result:
                        print(f"  {label}: {count_result['count']} nodes")
    
    # Close the driver connection
    driver.close()
    print("\nConnection test completed successfully")
    sys.exit(0)
    
except Exception as e:
    print(f"Error connecting to Neo4j: {str(e)}")
    sys.exit(1)
