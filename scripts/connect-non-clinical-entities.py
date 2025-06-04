#!/usr/bin/env python3
"""
Connect non-clinical entities to appropriate references.

This script adds reference connections to the remaining non-clinical entities in the 
dengue knowledge graph to ensure comprehensive evidence support:

Priority 1:
- Transmission Modes
- Prevention Measures
- Geographic Regions
- Climate Factors

Priority 2:
- Management Groups
- Warning Signs
- Vector Control Strategies
- Organizations
- Recommendations

Additional coverage for SNOMED terms where possible.
"""

import os
from neo4j import GraphDatabase, basic_auth

# Neo4j connection details
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'denguePassw0rd!')

# Connect to Neo4j
driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD))

def connect_transmission_modes(tx):
    """Connect TransmissionMode nodes to references."""
    # Add references to mosquito transmission
    query = """
    MATCH (tm:TransmissionMode {name: 'Mosquito Bite'})
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'vector' OR
        r.title CONTAINS 'Vector' OR
        r.title CONTAINS 'mosquito' OR
        r.title CONTAINS 'Mosquito' OR
        r.title CONTAINS 'transmission' OR
        r.title CONTAINS 'Transmission' OR
        r.title CONTAINS 'prevention' OR
        r.title CONTAINS 'Prevention'
    )
    MERGE (tm)-[:HAS_REFERENCE]->(r)
    RETURN count(r) as reference_count
    """
    result = tx.run(query)
    mosquito_count = result.single()["reference_count"]
    
    # Add references to maternal transmission
    query = """
    MATCH (tm:TransmissionMode {name: 'Maternal'})
    MATCH (r:Reference)
    WHERE (
        (r.title CONTAINS 'maternal' OR
        r.title CONTAINS 'Maternal' OR
        r.title CONTAINS 'transmission' OR
        r.title CONTAINS 'Transmission') 
        AND r.source_org IN ['WHO', 'CDC', 'PAHO']
    )
    MERGE (tm)-[:HAS_REFERENCE]->(r)
    RETURN count(r) as reference_count
    """
    result = tx.run(query)
    maternal_count = result.single()["reference_count"]
    
    # If no specific maternal refs, add general dengue guidelines
    if maternal_count == 0:
        query = """
        MATCH (tm:TransmissionMode {name: 'Maternal'})
        MATCH (r:Reference)
        WHERE r.title CONTAINS 'guideline' OR r.title CONTAINS 'Guideline'
        MERGE (tm)-[:HAS_REFERENCE]->(r)
        RETURN count(r) as reference_count
        """
        result = tx.run(query)
        maternal_count = result.single()["reference_count"]
    
    return mosquito_count, maternal_count

def connect_prevention_measures(tx):
    """Connect PreventionMeasure nodes to references."""
    # Get all prevention measures
    query = """
    MATCH (pm:PreventionMeasure)
    RETURN pm.name as name
    """
    result = tx.run(query)
    prevention_measures = [record["name"] for record in result]
    
    # Connect each prevention measure to relevant references
    results = {}
    for measure in prevention_measures:
        # Find key terms from the measure name
        terms = [term.lower() for term in measure.split() if len(term) > 3]
        
        term_conditions = []
        for term in terms:
            term_conditions.append(f"toLower(r.title) CONTAINS '{term}'")
        
        # Add general prevention terms
        term_conditions.extend([
            "r.title CONTAINS 'prevention'",
            "r.title CONTAINS 'Prevention'",
            "r.title CONTAINS 'control'",
            "r.title CONTAINS 'Control'"
        ])
        
        # If related to mosquitoes, add vector terms
        if "vector" in measure.lower() or "repellent" in measure.lower() or "mosquito" in measure.lower() or "larvae" in measure.lower() or "bed" in measure.lower() or "clothing" in measure.lower():
            term_conditions.extend([
                "r.title CONTAINS 'vector'",
                "r.title CONTAINS 'Vector'",
                "r.title CONTAINS 'mosquito'",
                "r.title CONTAINS 'Mosquito'"
            ])
            
        term_clause = " OR ".join(term_conditions)
        
        query = f"""
        MATCH (pm:PreventionMeasure {{name: '{measure}'}})
        MATCH (r:Reference)
        WHERE {term_clause}
        MERGE (pm)-[:HAS_REFERENCE]->(r)
        RETURN count(r) as reference_count
        """
        
        try:
            result = tx.run(query)
            count = result.single()["reference_count"]
            results[measure] = count
            
            # If no specific references found, connect to general guidelines
            if count == 0:
                query = f"""
                MATCH (pm:PreventionMeasure {{name: '{measure}'}})
                MATCH (r:Reference)
                WHERE r.title CONTAINS 'guideline' OR r.title CONTAINS 'Guideline'
                MERGE (pm)-[:HAS_REFERENCE]->(r)
                RETURN count(r) as reference_count
                """
                result = tx.run(query)
                results[measure] = result.single()["reference_count"]
        except Exception as e:
            # If there's an issue with special characters, try a more general approach
            query = f"""
            MATCH (pm:PreventionMeasure)
            WHERE pm.name = '{measure}'
            MATCH (r:Reference)
            WHERE r.title CONTAINS 'prevention' OR r.title CONTAINS 'Prevention'
            MERGE (pm)-[:HAS_REFERENCE]->(r)
            RETURN count(r) as reference_count
            """
            result = tx.run(query)
            results[measure] = result.single()["reference_count"]
    
    return results

def connect_geographic_regions(tx):
    """Connect GeographicRegion nodes to references."""
    # Connect Puerto Rico
    query = """
    MATCH (gr:GeographicRegion {name: 'Puerto Rico'})
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'Puerto Rico' OR
        r.title CONTAINS 'endemic' OR
        r.title CONTAINS 'Endemic' OR
        r.source_org = 'CDC'
    )
    MERGE (gr)-[:HAS_REFERENCE]->(r)
    RETURN count(r) as reference_count
    """
    result = tx.run(query)
    pr_count = result.single()["reference_count"]
    
    # Connect New Mexico
    query = """
    MATCH (gr:GeographicRegion {name: 'New Mexico'})
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'surveillance' OR
        r.title CONTAINS 'Surveillance' OR
        r.title CONTAINS 'epidemiology' OR
        r.title CONTAINS 'Epidemiology'
    )
    MERGE (gr)-[:HAS_REFERENCE]->(r)
    RETURN count(r) as reference_count
    """
    result = tx.run(query)
    nm_count = result.single()["reference_count"]
    
    return pr_count, nm_count

def connect_climate_factors(tx):
    """Connect ClimateFactor nodes to references."""
    query = """
    MATCH (cf:ClimateFactor)
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'climate' OR
        r.title CONTAINS 'Climate' OR
        r.title CONTAINS 'temperature' OR
        r.title CONTAINS 'Temperature' OR
        r.title CONTAINS 'rainfall' OR
        r.title CONTAINS 'Rainfall' OR
        r.title CONTAINS 'humidity' OR
        r.title CONTAINS 'Humidity' OR
        r.title CONTAINS 'vector' OR
        r.title CONTAINS 'Vector' OR
        r.title CONTAINS 'ecology' OR
        r.title CONTAINS 'Ecology' OR
        r.title CONTAINS 'environment' OR
        r.title CONTAINS 'Environment'
    )
    MERGE (cf)-[:HAS_REFERENCE]->(r)
    RETURN cf.name as factor, count(r) as reference_count
    """
    result = tx.run(query)
    return list(result)

def connect_management_groups(tx):
    """Connect ManagementGroup nodes to references."""
    query = """
    MATCH (mg:ManagementGroup)
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'management' OR
        r.title CONTAINS 'Management' OR
        r.title CONTAINS 'clinical' OR
        r.title CONTAINS 'Clinical' OR
        r.title CONTAINS 'treatment' OR
        r.title CONTAINS 'Treatment' OR
        r.title CONTAINS 'guideline' OR
        r.title CONTAINS 'Guideline'
    )
    MERGE (mg)-[:HAS_REFERENCE]->(r)
    RETURN mg.description as group, count(r) as reference_count
    """
    result = tx.run(query)
    return list(result)

def connect_warning_signs(tx):
    """Connect WarningSign nodes to references."""
    query = """
    MATCH (ws:WarningSign)
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'warning' OR
        r.title CONTAINS 'Warning' OR
        r.title CONTAINS 'sign' OR
        r.title CONTAINS 'Sign' OR
        r.title CONTAINS 'clinical' OR
        r.title CONTAINS 'Clinical' OR
        r.title CONTAINS 'symptom' OR
        r.title CONTAINS 'Symptom' OR
        r.title CONTAINS 'severe' OR
        r.title CONTAINS 'Severe'
    )
    MERGE (ws)-[:HAS_REFERENCE]->(r)
    RETURN ws.name as warning_sign, count(r) as reference_count
    """
    result = tx.run(query)
    return list(result)

def connect_vector_control(tx):
    """Connect VectorControl nodes to references."""
    query = """
    MATCH (vc:VectorControl)
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'vector' OR
        r.title CONTAINS 'Vector' OR
        r.title CONTAINS 'control' OR
        r.title CONTAINS 'Control' OR
        r.title CONTAINS 'prevention' OR
        r.title CONTAINS 'Prevention' OR
        r.title CONTAINS 'mosquito' OR
        r.title CONTAINS 'Mosquito'
    )
    MERGE (vc)-[:HAS_REFERENCE]->(r)
    RETURN vc.name as control_method, count(r) as reference_count
    """
    result = tx.run(query)
    return list(result)

def connect_organizations(tx):
    """Connect Organization nodes to references."""
    # Connect WHO
    query = """
    MATCH (org:Organization {name: 'World Health Organization'})
    MATCH (r:Reference)
    WHERE r.source_org = 'WHO'
    MERGE (org)-[:HAS_REFERENCE]->(r)
    RETURN count(r) as reference_count
    """
    result = tx.run(query)
    who_count = result.single()["reference_count"]
    
    # Connect CDC
    query = """
    MATCH (org:Organization {name: 'Centers for Disease Control and Prevention'})
    MATCH (r:Reference)
    WHERE r.source_org = 'CDC'
    MERGE (org)-[:HAS_REFERENCE]->(r)
    RETURN count(r) as reference_count
    """
    result = tx.run(query)
    cdc_count = result.single()["reference_count"]
    
    return who_count, cdc_count

def connect_recommendations(tx):
    """Connect Recommendation nodes to references."""
    query = """
    MATCH (rec:Recommendation)
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'recommendation' OR
        r.title CONTAINS 'Recommendation' OR
        r.title CONTAINS 'guideline' OR
        r.title CONTAINS 'Guideline' OR
        r.title CONTAINS 'evidence' OR
        r.title CONTAINS 'Evidence' OR
        r.title CONTAINS 'management' OR
        r.title CONTAINS 'Management' OR
        r.title CONTAINS 'clinical' OR
        r.title CONTAINS 'Clinical'
    )
    MERGE (rec)-[:HAS_REFERENCE]->(r)
    RETURN rec.description as recommendation, count(r) as reference_count
    """
    result = tx.run(query)
    return list(result)

def connect_remaining_snomed(tx):
    """Connect remaining SNOMED concept nodes to references."""
    # Connect organism SNOMED concepts (Aedes)
    query = """
    MATCH (sc:SnomedConcept {term: 'Aedes'})
    MATCH (r:Reference)
    WHERE r.title CONTAINS 'vector' OR r.title CONTAINS 'Vector' OR
          r.title CONTAINS 'mosquito' OR r.title CONTAINS 'Mosquito'
    MERGE (sc)-[:HAS_REFERENCE]->(r)
    RETURN count(r) as reference_count
    """
    result = tx.run(query)
    aedes_count = result.single()["reference_count"]
    
    # Connect procedure SNOMED concepts
    query = """
    MATCH (sc:SnomedConcept)
    WHERE sc.conceptType = 'procedure' AND NOT (sc)-[:HAS_REFERENCE]->()
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'diagnostic' OR
        r.title CONTAINS 'Diagnostic' OR
        r.title CONTAINS 'testing' OR
        r.title CONTAINS 'Testing' OR
        r.title CONTAINS 'laboratory' OR
        r.title CONTAINS 'Laboratory' OR
        r.title CONTAINS 'detection' OR
        r.title CONTAINS 'Detection'
    )
    MERGE (sc)-[:HAS_REFERENCE]->(r)
    RETURN count(DISTINCT sc) as concept_count, count(r) as reference_count
    """
    result = tx.run(query)
    procedure_record = result.single()
    
    # Connect remaining finding SNOMED concepts
    query = """
    MATCH (sc:SnomedConcept)
    WHERE sc.conceptType = 'finding' AND NOT (sc)-[:HAS_REFERENCE]->()
    MATCH (r:Reference)
    WHERE (
        r.title CONTAINS 'symptom' OR
        r.title CONTAINS 'Symptom' OR
        r.title CONTAINS 'clinical' OR
        r.title CONTAINS 'Clinical' OR
        r.title CONTAINS 'sign' OR
        r.title CONTAINS 'Sign' OR
        r.title CONTAINS 'warning' OR
        r.title CONTAINS 'Warning'
    )
    MERGE (sc)-[:HAS_REFERENCE]->(r)
    RETURN count(DISTINCT sc) as concept_count, count(r) as reference_count
    """
    result = tx.run(query)
    finding_record = result.single()
    
    return {
        "aedes_references": aedes_count,
        "procedure_concepts": procedure_record["concept_count"],
        "procedure_references": procedure_record["reference_count"],
        "finding_concepts": finding_record["concept_count"],
        "finding_references": finding_record["reference_count"]
    }

def get_overall_coverage():
    """Print overall reference coverage after connecting all entities."""
    with driver.session() as session:
        print('\n===== Overall Knowledge Graph Reference Coverage =====')
        
        # Count total nodes (excluding OntologyTerm and Reference)
        query = '''
        MATCH (n)
        WHERE NOT n:OntologyTerm AND NOT n:Reference
        RETURN count(n) as total_nodes
        '''
        total_nodes = session.run(query).single()['total_nodes']
        
        # Count nodes with references
        query = '''
        MATCH (n)-[:HAS_REFERENCE]->()
        WHERE NOT n:OntologyTerm AND NOT n:Reference
        RETURN count(DISTINCT n) as nodes_with_refs
        '''
        nodes_with_refs = session.run(query).single()['nodes_with_refs']
        
        overall_coverage = (nodes_with_refs / total_nodes * 100) if total_nodes > 0 else 0
        print(f'Overall Coverage: {nodes_with_refs}/{total_nodes} nodes ({overall_coverage:.1f}%)')
        
        # Get coverage by node type
        query = '''
        MATCH (n)
        WHERE NOT n:OntologyTerm AND NOT n:Reference
        WITH labels(n)[0] as node_type, count(n) as total
        OPTIONAL MATCH (m)
        WHERE labels(m)[0] = node_type AND (m)-[:HAS_REFERENCE]->()
        RETURN node_type, total, count(DISTINCT m) as with_refs
        ORDER BY total DESC
        '''
        
        result = session.run(query)
        
        print('\nReference Coverage by Node Type:')
        print('-' * 70)
        print(f'{"Node Type":<25} | {"Total":<8} | {"With Refs":<10} | {"Coverage":<10}')
        print('-' * 70)
        
        for record in result:
            node_type = record['node_type']
            total = record['total']
            with_refs = record['with_refs']
            
            coverage = (with_refs / total * 100) if total > 0 else 0
            print(f'{node_type:<25} | {total:<8} | {with_refs:<10} | {coverage:.1f}%')

def main():
    """Connect all remaining non-clinical entities to appropriate references."""
    with driver.session() as session:
        print("\n===== PRIORITY 1: CONNECTING SUPPORTING INFORMATION =====")
        
        print("\n--- Connecting Transmission Modes ---")
        mosquito_count, maternal_count = session.execute_write(connect_transmission_modes)
        print(f"Connected 'Mosquito Bite' transmission to {mosquito_count} references")
        print(f"Connected 'Maternal' transmission to {maternal_count} references")
        
        print("\n--- Connecting Prevention Measures ---")
        prevention_results = session.execute_write(connect_prevention_measures)
        for measure, count in prevention_results.items():
            print(f"Connected '{measure}' to {count} references")
        
        print("\n--- Connecting Geographic Regions ---")
        pr_count, nm_count = session.execute_write(connect_geographic_regions)
        print(f"Connected 'Puerto Rico' to {pr_count} references")
        print(f"Connected 'New Mexico' to {nm_count} references")
        
        print("\n--- Connecting Climate Factors ---")
        climate_results = session.execute_write(connect_climate_factors)
        for record in climate_results:
            print(f"Connected '{record['factor']}' to {record['reference_count']} references")
        
        print("\n===== PRIORITY 2: CONNECTING MANAGEMENT & OPERATIONAL DATA =====")
        
        print("\n--- Connecting Management Groups ---")
        management_results = session.execute_write(connect_management_groups)
        for record in management_results:
            print(f"Connected '{record['group']}' to {record['reference_count']} references")
        
        print("\n--- Connecting Warning Signs ---")
        warning_results = session.execute_write(connect_warning_signs)
        for record in warning_results:
            print(f"Connected '{record['warning_sign']}' to {record['reference_count']} references")
        
        print("\n--- Connecting Vector Control Strategies ---")
        control_results = session.execute_write(connect_vector_control)
        for record in control_results:
            print(f"Connected '{record['control_method']}' to {record['reference_count']} references")
        
        print("\n--- Connecting Organizations ---")
        who_count, cdc_count = session.execute_write(connect_organizations)
        print(f"Connected 'World Health Organization' to {who_count} references")
        print(f"Connected 'Centers for Disease Control and Prevention' to {cdc_count} references")
        
        print("\n--- Connecting Recommendations ---")
        recommendation_results = session.execute_write(connect_recommendations)
        for record in recommendation_results:
            description = record['recommendation'][:50] + "..." if len(record['recommendation']) > 50 else record['recommendation']
            print(f"Connected '{description}' to {record['reference_count']} references")
        
        print("\n--- Connecting Remaining SNOMED Concepts ---")
        snomed_results = session.execute_write(connect_remaining_snomed)
        print(f"Connected 'Aedes' SNOMED concept to {snomed_results['aedes_references']} references")
        print(f"Connected {snomed_results['procedure_concepts']} procedure concepts to {snomed_results['procedure_references']} references")
        print(f"Connected {snomed_results['finding_concepts']} finding concepts to {snomed_results['finding_references']} references")
        
        # Print final reference coverage
        get_overall_coverage()

if __name__ == "__main__":
    try:
        main()
        print("\nSuccessfully connected non-clinical entities to references!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()
