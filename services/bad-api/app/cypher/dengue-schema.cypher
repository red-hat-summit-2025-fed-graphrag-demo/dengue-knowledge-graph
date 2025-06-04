// Dengue Knowledge Graph - Schema Definition
// This file defines constraints and indexes for the Dengue Knowledge Graph

// Create constraints for core entities
CREATE CONSTRAINT disease_name IF NOT EXISTS
FOR (d:Disease) REQUIRE d.name IS UNIQUE;

CREATE CONSTRAINT symptom_name IF NOT EXISTS
FOR (s:Symptom) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT warning_sign_name IF NOT EXISTS
FOR (w:WarningSign) REQUIRE w.name IS UNIQUE;

CREATE CONSTRAINT clinical_classification_name IF NOT EXISTS
FOR (c:ClinicalClassification) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT clinical_manifestation_name IF NOT EXISTS
FOR (m:ClinicalManifestation) REQUIRE m.name IS UNIQUE;

CREATE CONSTRAINT diagnostic_test_name IF NOT EXISTS
FOR (t:DiagnosticTest) REQUIRE t.name IS UNIQUE;

CREATE CONSTRAINT treatment_protocol_id IF NOT EXISTS
FOR (t:TreatmentProtocol) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT vector_name IF NOT EXISTS
FOR (v:Vector) REQUIRE v.name IS UNIQUE;

CREATE CONSTRAINT region_id IF NOT EXISTS
FOR (r:Region) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT region_name IF NOT EXISTS
FOR (r:Region) REQUIRE r.name IS UNIQUE;

CREATE CONSTRAINT climate_factor_id IF NOT EXISTS
FOR (c:ClimateFactor) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT prevention_measure_id IF NOT EXISTS
FOR (p:PreventionMeasure) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT vector_control_id IF NOT EXISTS
FOR (v:VectorControl) REQUIRE v.id IS UNIQUE;

CREATE CONSTRAINT organization_id IF NOT EXISTS
FOR (o:Organization) REQUIRE o.id IS UNIQUE;

CREATE CONSTRAINT risk_factor_id IF NOT EXISTS
FOR (r:RiskFactor) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT recommendation_id IF NOT EXISTS
FOR (r:Recommendation) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT historical_data_id IF NOT EXISTS
FOR (h:HistoricalData) REQUIRE h.id IS UNIQUE;

CREATE CONSTRAINT prediction_data_id IF NOT EXISTS
FOR (p:PredictionData) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT snomed_concept_sctid IF NOT EXISTS
FOR (s:SnomedConcept) REQUIRE s.sctid IS UNIQUE;

CREATE CONSTRAINT ontology_term_id IF NOT EXISTS
FOR (o:OntologyTerm) REQUIRE o.id IS UNIQUE;

// Create fulltext search indexes
CALL db.index.fulltext.createNodeIndex(
  'diseaseAndSymptomSearch',
  ['Disease', 'Symptom', 'WarningSign', 'ClinicalManifestation'],
  ['name', 'description']
);

CALL db.index.fulltext.createNodeIndex(
  'clinicalSearch',
  ['ClinicalClassification', 'DiagnosticTest', 'TreatmentProtocol'],
  ['name', 'description']
);

CALL db.index.fulltext.createNodeIndex(
  'regionSearch',
  ['Region'],
  ['name', 'country', 'region_type']
);

// Create indexes for properties frequently used in queries
CREATE INDEX disease_name_idx IF NOT EXISTS FOR (d:Disease) ON (d.name);
CREATE INDEX symptom_name_idx IF NOT EXISTS FOR (s:Symptom) ON (s.name);
CREATE INDEX region_country_idx IF NOT EXISTS FOR (r:Region) ON (r.country);
CREATE INDEX historical_data_year_idx IF NOT EXISTS FOR (h:HistoricalData) ON (h.year);
CREATE INDEX prediction_data_date_idx IF NOT EXISTS FOR (p:PredictionData) ON (p.prediction_date);