#!/usr/bin/env python3
"""
Test script for Dengue Knowledge Graph API
Tests connectivity to the deployed API service and runs basic queries.
"""
import requests
import logging
import json
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# API connection details
API_BASE_URL = "https://dengue-api-neo4j-dengue-service.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com"

def test_api_connection():
    """Test connection to the API service and run basic requests"""
    try:
        # Test basic connectivity with the health endpoint
        logger.info(f"Testing connection to API at {API_BASE_URL}")
        
        # Health check endpoint
        health_url = f"{API_BASE_URL}/health"
        logger.info(f"Calling health endpoint: {health_url}")
        health_response = requests.get(health_url)
        
        if health_response.status_code == 200:
            logger.info(f"Health check successful! Response: {health_response.json()}")
        else:
            logger.warning(f"Health check failed with status code {health_response.status_code}")
            logger.warning(f"Response: {health_response.text}")
        
        # Try the root endpoint
        root_url = API_BASE_URL
        logger.info(f"Calling root endpoint: {root_url}")
        root_response = requests.get(root_url)
        
        if root_response.status_code == 200:
            logger.info(f"Root endpoint successful! Response: {root_response.json()}")
        else:
            logger.warning(f"Root endpoint failed with status code {root_response.status_code}")
            logger.warning(f"Response: {root_response.text}")
        
        # Check if the API has documentation
        docs_url = f"{API_BASE_URL}/docs"
        logger.info(f"Checking for API documentation: {docs_url}")
        docs_response = requests.get(docs_url)
        
        if docs_response.status_code == 200:
            logger.info("API documentation is available at /docs")
        else:
            logger.warning(f"API documentation endpoint failed with status code {docs_response.status_code}")
        
        # Try some API endpoints to see what's available
        endpoints_to_try = [
            "/api/v1/graph/info",
            "/api/v1/graph/stats",
            "/api/v1/dengue/symptoms",
            "/api/v1/dengue/classifications"
        ]
        
        for endpoint in endpoints_to_try:
            full_url = f"{API_BASE_URL}{endpoint}"
            logger.info(f"Testing endpoint: {full_url}")
            try:
                response = requests.get(full_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Endpoint {endpoint} successful!")
                    logger.info(f"Response preview: {json.dumps(data, indent=2)[:500]}...")
                else:
                    logger.warning(f"❌ Endpoint {endpoint} failed with status code {response.status_code}")
                    logger.warning(f"Response: {response.text[:500]}")
            except Exception as e:
                logger.error(f"Error calling endpoint {endpoint}: {str(e)}")
        
        logger.info("API connection test completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to API: {e}")
        return False

if __name__ == "__main__":
    success = test_api_connection()
    sys.exit(0 if success else 1)
