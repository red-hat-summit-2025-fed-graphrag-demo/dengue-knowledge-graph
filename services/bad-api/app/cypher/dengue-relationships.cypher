// Dengue Knowledge Graph - Relationship Definitions
// This file defines the core relationships between entities

// Connect disease to sub-classifications
MATCH (df:Disease {name: 'Dengue Fever'})
MATCH (sd:Disease {name: 'Severe Dengue'})
MERGE (df)-[:PROGRESSES_TO {risk_factors: 'Secondary infection, specific viral serotypes, host factors'}]->(sd);

// Connect symptoms to diseases
MATCH (d:Disease {name: 'Dengue Fever'})
MATCH (s:Symptom) 
WHERE s.name IN ['Fever', 'Headache', 'Myalgia', 'Arthralgia', 'Rash', 'Nausea', 'Vomiting'] 
MERGE (d)-[:HAS_SYMPTOM {frequency: 'Common'}]->(s);

// Connect severe manifestations to Severe Dengue
MATCH (d:Disease {name: 'Severe Dengue'})
MATCH (m:ClinicalManifestation)
MERGE (d)-[:HAS_MANIFESTATION]->(m);

// Connect diagnostic tests to diseases
MATCH (d:Disease)
WHERE d.name IN ['Dengue Fever', 'Severe Dengue']
MATCH (t:DiagnosticTest)
MERGE (d)-[:DIAGNOSED_BY {recommended: true}]->(t);

// Connect vectors to diseases
MATCH (d:Disease)
WHERE d.name IN ['Dengue Fever', 'Severe Dengue']
MATCH (v:Vector {name: 'Aedes aegypti'})
MERGE (v)-[:TRANSMITS {efficiency: 'High'}]->(d);

MATCH (d:Disease)
WHERE d.name IN ['Dengue Fever', 'Severe Dengue']
MATCH (v:Vector {name: 'Aedes albopictus'})
MERGE (v)-[:TRANSMITS {efficiency: 'Moderate'}]->(d);

// Connect symptoms to clinical classifications
MATCH (c:ClinicalClassification {name: 'Dengue without Warning Signs'})
MATCH (s:Symptom)
WHERE s.name IN ['Fever', 'Headache', 'Myalgia', 'Arthralgia', 'Rash', 'Nausea', 'Vomiting']
MERGE (c)-[:INCLUDES_SYMPTOM]->(s);

// Define clinical progression relationships
MATCH (c1:ClinicalClassification {name: 'Dengue without Warning Signs'})
MATCH (c2:ClinicalClassification {name: 'Dengue with Warning Signs'})
MATCH (c3:ClinicalClassification {name: 'Severe Dengue'})
MERGE (c1)-[:MAY_PROGRESS_TO {monitoring_requirement: 'Close monitoring for warning signs'}]->(c2)
MERGE (c2)-[:MAY_PROGRESS_TO {monitoring_requirement: 'Hospitalization recommended'}]->(c3);