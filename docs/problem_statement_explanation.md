# Problem Statement: Quantifying and Reducing Semantic Drift in Text-to-SQL Systems

## Overview
This document provides a comprehensive explanation of the problem statement for the project "Quantifying and Reducing Semantic Drift in Text-to-SQL Systems: A Constraint-Driven Multi-Agent Approach". It includes deep academic explanations, technical details, simple analogies, concrete examples, and 20 key research keywords.

## Deep Explanation
Semantic drift in natural language interfaces to databases (NLIDB) represents a fundamental challenge in human-computer interaction, where the inherent ambiguity and polysemy of natural language progressively diverges from the precise, unambiguous semantics required for structured query languages like SQL. This phenomenon manifests as a cascading failure across multiple abstraction layers: from lexical parsing through syntactic structuring to semantic grounding and logical execution. In text-to-SQL systems, drift emerges when natural language utterances are mapped to database schemas without sufficient contextual anchoring, leading to ontological mismatches, constraint violations, and result inaccuracies that compound over iterative interactions. The problem is exacerbated in enterprise environments where business rules, temporal constraints, and domain-specific ontologies introduce additional complexity, creating a multi-dimensional optimization space where traditional accuracy metrics fail to capture the nuanced degradation of query fidelity. Research in this domain reveals that semantic drift is not merely a technical artifact but a systemic issue rooted in the impedance mismatch between human cognitive models and machine-readable formalisms, necessitating novel approaches that integrate constraint satisfaction, provenance tracking, and adaptive learning mechanisms to maintain semantic integrity throughout the query lifecycle.

## Technical Explanation
Technically, semantic drift occurs during the transformation pipeline from natural language input to executable SQL queries. The process involves several stages: intent parsing (extracting entities, metrics, and filters), ontology mapping (aligning natural language concepts to database schemas), constraint validation (applying business rules), execution planning (generating parameterized SQL), and result verification (checking output plausibility). Drift manifests as:

1. **Intent Misalignment**: Cosine similarity between query embeddings and ontology paths falls below threshold
2. **Constraint Violations**: Business rules (e.g., tax exclusions, regional restrictions) are not satisfied
3. **Result Anomalies**: Statistical outliers detected via z-score analysis against historical baselines

The drift metric is formalized as: `drift = 0.4×(1-alignment) + 0.3×(1-adherence) + 0.3×(1-plausibility)`, where alignment measures semantic similarity, adherence tracks rule compliance, and plausibility detects anomalous results. In multi-agent architectures, drift accumulates across agent handoffs, with each agent potentially introducing errors through imperfect NLU, mapping ambiguities, or constraint misapplication. Without feedback loops, these errors propagate, resulting in queries that execute successfully but return semantically incorrect data.

## Simple Explanation
Imagine you're asking a friend to grab something from the kitchen, but they misunderstand and bring the wrong item. Semantic drift is like that misunderstanding getting worse over time in computer systems that translate everyday language into database queries. When you say "show me sales from last quarter," the system might think you mean "sales from last year" or "all sales ever," leading to wrong data. This happens because computers struggle with the fuzzy, context-dependent nature of human language compared to the strict rules of databases. Our project builds a team of "smart helpers" (agents) that check and double-check the translation, using business rules as guardrails to keep things accurate and prevent drift from building up.

## Examples

### Example 1: Basic Semantic Drift
**User Query**: "Show me customer orders from California"
**Intended SQL**: `SELECT * FROM orders WHERE customer_state = 'CA'`
**Drifted Interpretation**: System interprets "California" as "all west coast states" due to ambiguous geography
**Result**: Returns orders from CA, OR, WA, NV
**Drift Components**:
- Intent Alignment: 0.7 (partial match to regional ontology)
- Constraint Adherence: 0.5 (violates state-specific business rules)
- Result Plausibility: 0.8 (statistically plausible but incorrect)

### Example 2: Constraint Violation Drift
**User Query**: "Total revenue excluding taxes for Q1 2024"
**Intended SQL**: `SELECT SUM(amount) FROM transactions WHERE date BETWEEN '2024-01-01' AND '2024-03-31' AND tax_exempt = true`
**Drifted Interpretation**: Ignores tax exclusion constraint due to ontology mapping failure
**Result**: Includes taxable transactions, overestimating revenue
**Drift Components**:
- Intent Alignment: 0.9 (good temporal understanding)
- Constraint Adherence: 0.2 (major tax rule violation)
- Result Plausibility: 0.6 (anomalous revenue spike detected)

### Example 3: Multi-Agent Drift Accumulation
**User Query**: "Compare product performance across regions last month"
**Pipeline Stages**:
1. IntentParser: Extracts "product", "performance", "regions", "last month" (confidence: 0.95)
2. OntologyMapper: Maps "performance" to "sales_volume" but misses "profit_margin" (drift introduced)
3. ConstraintValidator: Applies regional access rules but allows unauthorized data (drift accumulates)
4. ExecutionPlanner: Generates SQL with incorrect joins (drift propagates)
5. ResultVerifier: Passes anomalous results due to insufficient baselines (drift undetected)
**Final Drift Score**: 0.65 (severe misalignment)

## 20 Key Research Keywords
1. Semantic Drift
2. Text-to-SQL
3. Natural Language Interfaces to Databases (NLIDB)
4. Multi-Agent Systems
5. Constraint-Driven Architecture
6. Ontology Mapping
7. Query Provenance
8. Drift Detection
9. Semantic Grounding
10. Business Rule Validation
11. Intent Alignment
12. Constraint Adherence
13. Result Plausibility
14. Critic Loop Architecture
15. Embedding Similarity
16. Anomaly Detection
17. Z-Score Analysis
18. Cosine Similarity
19. Formal Ontology
20. Governance Compliance</content>
<parameter name="filePath">c:\Users\THARUN G\Desktop\FYP\problem_statement_explanation.md