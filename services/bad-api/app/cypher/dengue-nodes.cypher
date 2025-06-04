// Dengue Knowledge Graph - Base Node Definitions
// This file defines the core nodes for the Dengue Knowledge Graph

// Disease nodes
MERGE (dengue:Disease {name: 'Dengue Fever'})
ON CREATE SET dengue.description = 'A mosquito-borne viral disease that causes a wide spectrum of disease. Classic dengue fever is a mild febrile illness characterized by headache, retroorbital pain, muscle and joint pains, nausea, vomiting, and often a rash.',
              dengue.icd10_code = 'A90',
              dengue.pathogen = 'Dengue virus (DENV)',
              dengue.transmission = 'Vector-borne (Aedes mosquitoes)',
              dengue.incubation_period = '4-10 days (range 3-14 days)';

MERGE (sd:Disease {name: 'Severe Dengue'})
ON CREATE SET sd.description = 'A severe form of dengue characterized by plasma leakage, hemorrhage, and organ impairment. Formerly known as Dengue Hemorrhagic Fever (DHF) and Dengue Shock Syndrome (DSS).',
              sd.icd10_code = 'A91',
              sd.pathogen = 'Dengue virus (DENV)',
              sd.transmission = 'Vector-borne (Aedes mosquitoes)',
              sd.incubation_period = '4-10 days (range 3-14 days)';

// Clinical Classification nodes
MERGE (c1:ClinicalClassification {name: 'Dengue without Warning Signs'})
ON CREATE SET c1.description = 'Fever and two of the following: nausea/vomiting, rash, aches and pains, positive tourniquet test, leukopenia, any warning sign';

MERGE (c2:ClinicalClassification {name: 'Dengue with Warning Signs'})
ON CREATE SET c2.description = 'Dengue as defined above with any of the following: abdominal pain or tenderness, persistent vomiting, clinical fluid accumulation, mucosal bleeding, lethargy, restlessness, liver enlargement >2 cm, laboratory: increase in HCT concurrent with rapid decrease in platelet count';

MERGE (c3:ClinicalClassification {name: 'Severe Dengue'})
ON CREATE SET c3.description = 'Dengue with at least one of the following: severe plasma leakage leading to shock (DSS), fluid accumulation with respiratory distress; severe bleeding as evaluated by clinician; severe organ involvement such as liver (AST or ALT ≥1000), CNS (impaired consciousness), heart and other organs';

// Connect clinical classifications to diseases
MATCH (d:Disease {name: 'Dengue Fever'})
MATCH (c:ClinicalClassification {name: 'Dengue without Warning Signs'})
MERGE (d)-[:HAS_CLASSIFICATION]->(c);

MATCH (d:Disease {name: 'Dengue Fever'})
MATCH (c:ClinicalClassification {name: 'Dengue with Warning Signs'})
MERGE (d)-[:HAS_CLASSIFICATION]->(c);

MATCH (d:Disease {name: 'Severe Dengue'})
MATCH (c:ClinicalClassification {name: 'Severe Dengue'})
MERGE (d)-[:HAS_CLASSIFICATION]->(c);

// Warning Signs
MERGE (ws1:WarningSign {name: 'Abdominal Pain or Tenderness'})
ON CREATE SET ws1.description = 'Persistent or increasing abdominal pain or tenderness';

MERGE (ws2:WarningSign {name: 'Persistent Vomiting'})
ON CREATE SET ws2.description = 'Three or more episodes in 24 hours';

MERGE (ws3:WarningSign {name: 'Clinical Fluid Accumulation'})
ON CREATE SET ws3.description = 'Pleural effusion or ascites confirmed by imaging';

MERGE (ws4:WarningSign {name: 'Mucosal Bleeding'})
ON CREATE SET ws4.description = 'Bleeding from mucosal surfaces including gums, nose, vagina, etc.';

MERGE (ws5:WarningSign {name: 'Lethargy or Restlessness'})
ON CREATE SET ws5.description = 'Change in mental state, lethargy or restlessness';

MERGE (ws6:WarningSign {name: 'Liver Enlargement'})
ON CREATE SET ws6.description = 'Hepatomegaly >2cm';

MERGE (ws7:WarningSign {name: 'Laboratory: Increased HCT with Rapid Platelet Drop'})
ON CREATE SET ws7.description = 'Increase in hematocrit concurrent with rapid decrease in platelet count';

// Connect warning signs to clinical classification
MATCH (c:ClinicalClassification {name: 'Dengue with Warning Signs'})
MATCH (ws:WarningSign)
MERGE (c)-[:INCLUDES_WARNING_SIGN]->(ws);

// Symptoms
MERGE (s1:Symptom {name: 'Fever'})
ON CREATE SET s1.description = 'High fever, typically 39-40°C (102-104°F)';

MERGE (s2:Symptom {name: 'Headache'})
ON CREATE SET s2.description = 'Severe headache, often with retroorbital pain';

MERGE (s3:Symptom {name: 'Myalgia'})
ON CREATE SET s3.description = 'Muscle pain or myalgia';

MERGE (s4:Symptom {name: 'Arthralgia'})
ON CREATE SET s4.description = 'Joint pain';

MERGE (s5:Symptom {name: 'Rash'})
ON CREATE SET s5.description = 'Maculopapular or petechial rash, usually appearing 3-4 days after fever onset';

MERGE (s6:Symptom {name: 'Nausea'})
ON CREATE SET s6.description = 'Feeling of sickness with an inclination to vomit';

MERGE (s7:Symptom {name: 'Vomiting'})
ON CREATE SET s7.description = 'Forceful expulsion of stomach contents through the mouth';

// Clinical Manifestations for Severe Dengue
MERGE (m1:ClinicalManifestation {name: 'Plasma Leakage'})
ON CREATE SET m1.description = 'Increased vascular permeability leading to plasma leakage, resulting in fluid accumulation in pleural and abdominal cavities';

MERGE (m2:ClinicalManifestation {name: 'Shock'})
ON CREATE SET m2.description = 'Dengue shock syndrome (DSS) characterized by rapid, weak pulse, narrow pulse pressure or hypotension, cold, clammy skin, and restlessness';

MERGE (m3:ClinicalManifestation {name: 'Severe Bleeding'})
ON CREATE SET m3.description = 'Severe bleeding manifestations, such as hematemesis, melena, or significant mucosal bleeding';

MERGE (m4:ClinicalManifestation {name: 'Organ Impairment'})
ON CREATE SET m4.description = 'Severe involvement of liver (AST or ALT ≥1000), central nervous system (impaired consciousness), heart, or other organs';

// Diagnostic Tests
MERGE (t1:DiagnosticTest {name: 'NS1 Antigen Test'})
ON CREATE SET t1.description = 'Detects dengue virus NS1 antigen in serum, plasma, or whole blood',
              t1.sample_type = 'Blood',
              t1.detection_window = 'Day 0-5 after symptom onset',
              t1.test_type = 'Rapid diagnostic test or ELISA',
              t1.sensitivity = '60-90% depending on timing',
              t1.specificity = '95-100%';

MERGE (t2:DiagnosticTest {name: 'IgM ELISA'})
ON CREATE SET t2.description = 'Detects dengue-specific IgM antibodies',
              t2.sample_type = 'Blood',
              t2.detection_window = 'Day 4-5 after symptom onset to 2-3 months',
              t2.test_type = 'Enzyme-linked immunosorbent assay',
              t2.sensitivity = '80-90% after day 5',
              t2.specificity = '90-95%';

MERGE (t3:DiagnosticTest {name: 'RT-PCR'})
ON CREATE SET t3.description = 'Detects dengue virus RNA',
              t3.sample_type = 'Blood',
              t3.detection_window = 'Day 0-5 after symptom onset',
              t3.test_type = 'Molecular test',
              t3.sensitivity = '90-95% in early acute phase',
              t3.specificity = '95-100%';

MERGE (t4:DiagnosticTest {name: 'Complete Blood Count'})
ON CREATE SET t4.description = 'Monitoring of hematocrit (Hct) and platelet count',
              t4.sample_type = 'Blood',
              t4.detection_window = 'Throughout illness',
              t4.test_type = 'Hematology',
              t4.sensitivity = 'N/A (monitoring test)',
              t4.specificity = 'N/A (monitoring test)';

// Vector
MERGE (v1:Vector {name: 'Aedes aegypti'})
ON CREATE SET v1.description = 'Primary mosquito vector for dengue transmission',
              v1.geographic_distribution = 'Tropical and subtropical regions worldwide',
              v1.behavior = 'Day-biting, highly anthropophilic, indoor-resting';

MERGE (v2:Vector {name: 'Aedes albopictus'})
ON CREATE SET v2.description = 'Secondary mosquito vector for dengue transmission',
              v2.geographic_distribution = 'Wider geographic range, including temperate regions',
              v2.behavior = 'Outdoor-biting, less anthropophilic than Ae. aegypti';