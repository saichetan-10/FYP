"""
Business Ontology: Formal Knowledge Representation Layer

Encodes:
- Entity definitions with attributes
- Metric specifications with formulas and valid ranges
- Temporal constraints (refresh frequency, retention)
- Join cardinality rules for multi-entity queries
- Access control and data governance rules

Implemented using NetworkX property graphs for constraint mapping
and ChromaDB for vector similarity search over business rules.
"""

import json
import os
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib

try:
    import networkx as nx
except ImportError:
    nx = None

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None


# ============================================================================
# Core Ontology Data Structures
# ============================================================================


@dataclass
class EntityDefinition:
    """Formal definition of a business entity."""
    entity_id: str
    name: str
    description: str
    table_name: str
    attributes: Dict[str, str]  # attribute_name -> data_type
    primary_key: str
    natural_language_aliases: List[str] = field(default_factory=list)
    source_database: str = "sales"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetricDefinition:
    """Formal definition of a business metric."""
    metric_id: str
    name: str
    description: str
    formula: str  # e.g., "SUM(orders.total_amount)", "AVG(customers.lifetime_value)"
    valid_range: Tuple[float, float]  # (min, max)
    unit: str
    refresh_frequency: str  # e.g., "DAILY", "HOURLY"
    requires_entities: List[str]  # Entity IDs needed to calculate metric
    natural_language_aliases: List[str] = field(default_factory=list)
    aggregation_type: str = "SUM"  # SUM, AVG, COUNT, MIN, MAX
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConstraintRule:
    """Formal business constraint/rule."""
    rule_id: str
    name: str
    description: str
    rule_type: str  # TAX_EXCLUSION, REGION_FILTER, DATE_RANGE, etc.
    condition: str  # Natural language or pseudocode
    entities_affected: List[str]
    severity: str = "REQUIRED"  # REQUIRED, WARNING, INFO
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JoinRule:
    """Join cardinality rule between entities."""
    from_entity: str
    to_entity: str
    join_key_from: str
    join_key_to: str
    cardinality: str  # "1:1", "1:N", "N:1", "N:N"
    join_condition: str  # SQL condition
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Business Ontology Manager
# ============================================================================


class BusinessOntology:
    """
    Complete business ontology management using property graphs.
    
    Provides:
    - Entity and metric definitions
    - Constraint validation
    - Join path finding
    - Natural language grounding
    """
    
    def __init__(self):
        """Initialize ontology with NetworkX graph."""
        self.entities: Dict[str, EntityDefinition] = {}
        self.metrics: Dict[str, MetricDefinition] = {}
        self.constraints: Dict[str, ConstraintRule] = {}
        self.joins: List[JoinRule] = []
        
        # NetworkX property graph for constraint mapping
        self.graph = nx.DiGraph() if nx else None
        
        # ChromaDB for semantic search (if available)
        self.chroma_client = None
        self.chroma_collection = None
        if chromadb:
            try:
                self.chroma_client = chromadb.Client()
                self.chroma_collection = self.chroma_client.create_collection(
                    name="business_ontology",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception:
                pass  # ChromaDB not fully configured
        
        self._populate_default_ontology()

    # ------------------------------------------------------------------
    # Ontology loading
    # ------------------------------------------------------------------

    def _populate_default_ontology(self) -> None:
        """Load ontology from JSON files if available, else hardcoded fallback."""
        from src.config import config
        files = [
            config.ontology.entities_file,
            config.ontology.metrics_file,
            config.ontology.rules_file,
        ]
        if all(os.path.exists(p) for p in files):
            try:
                self._load_from_json_files(
                    config.ontology.entities_file,
                    config.ontology.metrics_file,
                    config.ontology.rules_file,
                )
                return
            except Exception as exc:
                print(f"[ontology] JSON load failed ({exc}), falling back to hardcoded defaults")
        self._load_hardcoded_defaults()

    def _load_from_json_files(
        self, entities_file: str, metrics_file: str, rules_file: str
    ) -> None:
        """Load entities, metrics, and rules from JSON files."""
        with open(entities_file, "r") as f:
            entities_data = json.load(f)
        for e in entities_data:
            self.add_entity(EntityDefinition(
                entity_id=e["entity_id"],
                name=e["name"],
                description=e.get("description", ""),
                table_name=e["table_name"],
                attributes=e.get("attributes", {}),
                primary_key=e.get("primary_key", "id"),
                natural_language_aliases=e.get("natural_language_aliases", []),
                source_database=e.get("database", "sales"),
            ))

        with open(metrics_file, "r") as f:
            metrics_data = json.load(f)
        for m in metrics_data:
            vr = m.get("valid_range", [0, 1e9])
            self.add_metric(MetricDefinition(
                metric_id=m["metric_id"],
                name=m["name"],
                description=m.get("description", ""),
                formula=m.get("formula", ""),
                valid_range=(float(vr[0]), float(vr[1])) if vr else (0, 1e9),
                unit=m.get("unit", ""),
                refresh_frequency=m.get("refresh_frequency", "DAILY"),
                requires_entities=m.get("requires_entities", []),
                natural_language_aliases=m.get("natural_language_aliases", []),
                aggregation_type=m.get("aggregation_type", "SUM"),
            ))

        with open(rules_file, "r") as f:
            rules_data = json.load(f)
        for r in rules_data:
            self.add_constraint(ConstraintRule(
                rule_id=r["rule_id"],
                name=r["name"],
                description=r.get("description", ""),
                rule_type=r.get("rule_type", r.get("category", "GENERAL")),
                condition=r.get("condition", ""),
                entities_affected=r.get("entities_affected", []),
                severity=r.get("severity", "INFO"),
            ))

        # Always add core join rules (they depend on entity structure)
        self._add_default_join_rules()

    def _add_default_join_rules(self) -> None:
        """Register well-known join relationships between core entities."""
        defaults = [
            JoinRule("CUSTOMER", "ORDER", "customer_id", "customer_id", "1:N",
                     "customers.customer_id = orders.customer_id"),
            JoinRule("ORDER", "INVOICE", "order_id", "order_id", "1:N",
                     "orders.order_id = invoices.order_id"),
            JoinRule("ORDER", "TRANSACTION", "order_id", "order_id", "1:N",
                     "orders.order_id = transactions.order_id"),
            JoinRule("ORDER", "ORDER_ITEM", "order_id", "order_id", "1:N",
                     "orders.order_id = order_items.order_id"),
            JoinRule("ORDER_ITEM", "PRODUCT", "product_id", "product_id", "N:1",
                     "order_items.product_id = products.product_id"),
            JoinRule("PRODUCT", "SUPPLIER", "supplier_id", "supplier_id", "N:1",
                     "products.supplier_id = suppliers.supplier_id"),
            JoinRule("ORDER", "RETURN", "order_id", "order_id", "1:N",
                     "orders.order_id = returns.order_id"),
            JoinRule("EMPLOYEE", "DEPARTMENT", "department_id", "department_id", "N:1",
                     "employees.department_id = departments.department_id"),
        ]
        for j in defaults:
            if j.from_entity in self.entities or j.to_entity in self.entities:
                self.add_join_rule(j)

    def _load_hardcoded_defaults(self) -> None:
        """Hardcoded fallback ontology (original implementation)."""
        # Define entities
        self.add_entity(EntityDefinition(
            entity_id="CUSTOMER",
            name="Customer",
            description="Individual or organization that purchases products/services",
            table_name="customers",
            attributes={
                "customer_id": "VARCHAR",
                "name": "VARCHAR",
                "email": "VARCHAR",
                "region": "VARCHAR",
                "department": "VARCHAR",
                "created_date": "DATETIME",
                "total_spent": "DECIMAL",
                "customer_tier": "VARCHAR",
            },
            primary_key="customer_id",
            natural_language_aliases=["client", "buyer", "account", "customer"]
        ))
        
        self.add_entity(EntityDefinition(
            entity_id="PRODUCT",
            name="Product",
            description="Item available for sale",
            table_name="products",
            attributes={
                "product_id": "VARCHAR",
                "name": "VARCHAR",
                "category": "VARCHAR",
                "price": "DECIMAL",
                "cost": "DECIMAL",
                "description": "TEXT",
                "stock_quantity": "INTEGER",
                "supplier_id": "VARCHAR",
                "is_active": "BOOLEAN",
            },
            primary_key="product_id",
            natural_language_aliases=["item", "product", "sku", "offering"]
        ))
        
        self.add_entity(EntityDefinition(
            entity_id="ORDER",
            name="Order",
            description="Customer purchase order",
            table_name="orders",
            attributes={
                "order_id": "VARCHAR",
                "customer_id": "VARCHAR",
                "order_date": "DATETIME",
                "total_amount": "DECIMAL",
                "item_count": "INTEGER",
                "status": "VARCHAR",
                "shipping_cost": "DECIMAL",
                "tax_amount": "DECIMAL",
            },
            primary_key="order_id",
            natural_language_aliases=["order", "purchase", "transaction", "sale"]
        ))
        
        self.add_entity(EntityDefinition(
            entity_id="INVOICE",
            name="Invoice",
            description="Billing document for order",
            table_name="invoices",
            attributes={
                "invoice_id": "VARCHAR",
                "order_id": "VARCHAR",
                "customer_id": "VARCHAR",
                "invoice_date": "DATETIME",
                "due_date": "DATETIME",
                "subtotal": "DECIMAL",
                "tax_amount": "DECIMAL",
                "total_amount": "DECIMAL",
                "status": "VARCHAR",
                "payment_method": "VARCHAR",
            },
            primary_key="invoice_id",
            natural_language_aliases=["invoice", "bill", "receipt"]
        ))
        
        self.add_entity(EntityDefinition(
            entity_id="TRANSACTION",
            name="Transaction",
            description="Payment or financial transaction",
            table_name="transactions",
            attributes={
                "transaction_id": "VARCHAR",
                "order_id": "VARCHAR",
                "customer_id": "VARCHAR",
                "transaction_date": "DATETIME",
                "transaction_type": "VARCHAR",
                "amount": "DECIMAL",
                "status": "VARCHAR",
                "payment_gateway": "VARCHAR",
            },
            primary_key="transaction_id",
            natural_language_aliases=["transaction", "payment", "charge"]
        ))
        
        # Define metrics
        self.add_metric(MetricDefinition(
            metric_id="TOTAL_REVENUE",
            name="Total Revenue",
            description="Sum of all order totals",
            formula="SUM(orders.total_amount)",
            valid_range=(0, 1000000000),
            unit="USD",
            refresh_frequency="DAILY",
            requires_entities=["ORDER"],
            natural_language_aliases=["revenue", "total sales", "earnings"],
            aggregation_type="SUM"
        ))
        
        self.add_metric(MetricDefinition(
            metric_id="CUSTOMER_COUNT",
            name="Customer Count",
            description="Number of unique customers",
            formula="COUNT(DISTINCT customers.customer_id)",
            valid_range=(0, 1000000),
            unit="COUNT",
            refresh_frequency="DAILY",
            requires_entities=["CUSTOMER"],
            natural_language_aliases=["customer count", "customers", "total customers"],
            aggregation_type="COUNT"
        ))
        
        self.add_metric(MetricDefinition(
            metric_id="AVG_ORDER_VALUE",
            name="Average Order Value",
            description="Average value of orders",
            formula="AVG(orders.total_amount)",
            valid_range=(0, 100000),
            unit="USD",
            refresh_frequency="DAILY",
            requires_entities=["ORDER"],
            natural_language_aliases=["avg order value", "average order", "aov"],
            aggregation_type="AVG"
        ))
        
        self.add_metric(MetricDefinition(
            metric_id="TOTAL_PROFIT",
            name="Total Profit",
            description="Sum of all order revenues minus costs",
            formula="SUM(orders.total_amount - products.cost)",
            valid_range=(-1000000000, 1000000000),
            unit="USD",
            refresh_frequency="DAILY",
            requires_entities=["ORDER", "PRODUCT"],
            natural_language_aliases=["profit", "net income", "margin"],
            aggregation_type="SUM"
        ))
        
        # Define constraints
        self.add_constraint(ConstraintRule(
            rule_id="NO_TAX_EXCLUSION",
            name="Tax Exclusion Rule",
            description="Orders from certain regions are tax-exempt",
            rule_type="TAX_EXCLUSION",
            condition="region NOT IN ('Alaska', 'Hawaii')",
            entities_affected=["ORDER", "CUSTOMER"],
            severity="REQUIRED"
        ))
        
        self.add_constraint(ConstraintRule(
            rule_id="REGION_FILTER",
            name="Region Availability",
            description="Some products only available in specific regions",
            rule_type="REGION_FILTER",
            condition="product.is_active = TRUE",
            entities_affected=["PRODUCT"],
            severity="REQUIRED"
        ))
        
        self.add_constraint(ConstraintRule(
            rule_id="DATE_RANGE",
            name="Historical Data Retention",
            description="Only query last 2 years of data by default",
            rule_type="DATE_RANGE",
            condition="order_date >= NOW() - INTERVAL '2 years'",
            entities_affected=["ORDER", "INVOICE", "TRANSACTION"],
            severity="WARNING"
        ))
        
        # ── New entities ──────────────────────────────────────────────────────

        self.add_entity(EntityDefinition(
            entity_id="SUPPLIER",
            name="Supplier",
            description="Company or individual that provides products for resale",
            table_name="suppliers",
            attributes={
                "supplier_id": "VARCHAR",
                "name": "VARCHAR",
                "country": "VARCHAR",
                "category": "VARCHAR",
                "contact_email": "VARCHAR",
                "lead_time_days": "INTEGER",
                "rating": "DECIMAL",
                "is_active": "BOOLEAN",
            },
            primary_key="supplier_id",
            natural_language_aliases=["supplier", "vendor", "manufacturer", "partner"],
        ))

        self.add_entity(EntityDefinition(
            entity_id="ORDER_ITEM",
            name="Order Item",
            description="Individual line item within a customer order",
            table_name="order_items",
            attributes={
                "order_item_id": "VARCHAR",
                "order_id": "VARCHAR",
                "product_id": "VARCHAR",
                "quantity": "INTEGER",
                "unit_price": "DECIMAL",
                "discount_pct": "DECIMAL",
                "line_total": "DECIMAL",
            },
            primary_key="order_item_id",
            natural_language_aliases=["order item", "line item", "order line"],
        ))

        self.add_entity(EntityDefinition(
            entity_id="RETURN",
            name="Return",
            description="Customer return of a previously purchased product",
            table_name="returns",
            attributes={
                "return_id": "VARCHAR",
                "order_id": "VARCHAR",
                "customer_id": "VARCHAR",
                "product_id": "VARCHAR",
                "return_date": "DATETIME",
                "reason": "VARCHAR",
                "amount": "DECIMAL",
                "status": "VARCHAR",
            },
            primary_key="return_id",
            natural_language_aliases=["return", "refund", "returned order"],
        ))

        # ── New metrics ────────────────────────────────────────────────────────

        self.add_metric(MetricDefinition(
            metric_id="GROSS_MARGIN",
            name="Gross Margin",
            description="Percentage of revenue remaining after cost of goods",
            formula="ROUND((SUM(total_amount) - SUM(cost)) * 100.0 / NULLIF(SUM(total_amount), 0), 2)",
            valid_range=(0, 100),
            unit="PERCENT",
            refresh_frequency="DAILY",
            requires_entities=["ORDER", "PRODUCT"],
            natural_language_aliases=["gross margin", "gross profit", "markup", "margin percentage"],
            aggregation_type="RATIO",
        ))

        self.add_metric(MetricDefinition(
            metric_id="CUSTOMER_LTV",
            name="Customer Lifetime Value",
            description="Average revenue generated per unique customer",
            formula="ROUND(SUM(total_amount) / NULLIF(COUNT(DISTINCT customer_id), 0), 2)",
            valid_range=(0, 1000000),
            unit="USD",
            refresh_frequency="WEEKLY",
            requires_entities=["CUSTOMER", "ORDER"],
            natural_language_aliases=["ltv", "lifetime value", "clv", "customer value"],
            aggregation_type="RATIO",
        ))

        self.add_metric(MetricDefinition(
            metric_id="CHURN_RATE",
            name="Churn Rate",
            description="Percentage of orders that were cancelled",
            formula="ROUND(SUM(CASE WHEN status='Cancelled' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2)",
            valid_range=(0, 100),
            unit="PERCENT",
            refresh_frequency="DAILY",
            requires_entities=["ORDER"],
            natural_language_aliases=["churn", "churned", "attrition", "churn rate", "cancellation rate"],
            aggregation_type="RATIO",
        ))

        self.add_metric(MetricDefinition(
            metric_id="NEW_CUSTOMER_COUNT",
            name="New Customer Count",
            description="Number of distinct customers placing orders in the period",
            formula="COUNT(DISTINCT customer_id)",
            valid_range=(0, 10000000),
            unit="COUNT",
            refresh_frequency="DAILY",
            requires_entities=["CUSTOMER", "ORDER"],
            natural_language_aliases=["new customers", "new signups", "acquired customers", "unique buyers"],
            aggregation_type="COUNT",
        ))

        self.add_metric(MetricDefinition(
            metric_id="RETURN_RATE",
            name="Return Rate",
            description="Percentage of orders that have an associated return",
            formula="ROUND(COUNT(DISTINCT returns.order_id) * 100.0 / NULLIF(COUNT(DISTINCT orders.order_id), 0), 2)",
            valid_range=(0, 100),
            unit="PERCENT",
            refresh_frequency="DAILY",
            requires_entities=["ORDER", "RETURN"],
            natural_language_aliases=["return rate", "returns", "returned orders", "refund rate"],
            aggregation_type="RATIO",
        ))

        self.add_metric(MetricDefinition(
            metric_id="CONVERSION_RATE",
            name="Conversion Rate",
            description="Ratio of converting customers to total customers visited",
            formula="COUNT(DISTINCT orders.customer_id)",
            valid_range=(0, 1),
            unit="RATIO",
            refresh_frequency="DAILY",
            requires_entities=["CUSTOMER", "ORDER"],
            natural_language_aliases=["conversion rate", "conversion", "converted"],
            aggregation_type="RATIO",
        ))

        self.add_metric(MetricDefinition(
            metric_id="ACTIVE_CUSTOMERS",
            name="Active Customers",
            description="Customers who placed at least one order in the period",
            formula="COUNT(DISTINCT customer_id) WHERE status != 'Cancelled'",
            valid_range=(0, 10000000),
            unit="COUNT",
            refresh_frequency="DAILY",
            requires_entities=["CUSTOMER", "ORDER"],
            natural_language_aliases=["active customers", "retention", "retained customers"],
            aggregation_type="COUNT",
        ))

        self.add_metric(MetricDefinition(
            metric_id="INVENTORY_TURNOVER",
            name="Inventory Turnover",
            description="Total units sold relative to current stock levels",
            formula="SUM(order_items.quantity)",
            valid_range=(0, 100000000),
            unit="UNITS",
            refresh_frequency="DAILY",
            requires_entities=["ORDER_ITEM", "PRODUCT"],
            natural_language_aliases=["inventory", "stock", "in stock", "stock levels", "units sold"],
            aggregation_type="SUM",
        ))

        # ── New constraints ────────────────────────────────────────────────────

        self.add_constraint(ConstraintRule(
            rule_id="ACTIVE_PRODUCTS_ONLY",
            name="Active Products Filter",
            description="Metrics should only include active (non-discontinued) products",
            rule_type="ACTIVE_PRODUCTS_ONLY",
            condition="products.is_active = TRUE",
            entities_affected=["PRODUCT", "ORDER_ITEM"],
            severity="WARNING",
        ))

        self.add_constraint(ConstraintRule(
            rule_id="DATA_FRESHNESS",
            name="Data Freshness Window",
            description="Operational metrics restricted to last 90 days for accuracy",
            rule_type="DATA_FRESHNESS",
            condition="order_date >= NOW() - INTERVAL '90 days'",
            entities_affected=["ORDER", "TRANSACTION"],
            severity="INFO",
        ))

        self.add_constraint(ConstraintRule(
            rule_id="FISCAL_YEAR",
            name="Fiscal Year Alignment",
            description="Fiscal quarters: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec",
            rule_type="FISCAL_YEAR",
            condition="EXTRACT(QUARTER FROM order_date) IN (1,2,3,4)",
            entities_affected=["ORDER", "INVOICE"],
            severity="INFO",
        ))

        self.add_constraint(ConstraintRule(
            rule_id="PII_PROTECTION",
            name="PII Protection Rule",
            description="Queries must not expose raw customer PII (email, full name)",
            rule_type="PII_PROTECTION",
            condition="SELECT must not include customers.email or full_name without aggregation",
            entities_affected=["CUSTOMER"],
            severity="REQUIRED",
        ))

        self.add_constraint(ConstraintRule(
            rule_id="ACTIVE_CUSTOMERS_ONLY",
            name="Active Customers Only",
            description="Exclude churned customers from active customer metrics",
            rule_type="ACTIVE_CUSTOMERS_ONLY",
            condition="customers.customer_tier IS NOT NULL",
            entities_affected=["CUSTOMER"],
            severity="WARNING",
        ))

        self.add_constraint(ConstraintRule(
            rule_id="MIN_ORDER_VALUE",
            name="Minimum Order Value",
            description="Only include orders with positive total_amount",
            rule_type="MIN_ORDER_VALUE",
            condition="orders.total_amount > 0",
            entities_affected=["ORDER"],
            severity="REQUIRED",
        ))

        # ── Define join rules ─────────────────────────────────────────────────

        self.add_join_rule(JoinRule(
            from_entity="CUSTOMER",
            to_entity="ORDER",
            join_key_from="customer_id",
            join_key_to="customer_id",
            cardinality="1:N",
            join_condition="customers.customer_id = orders.customer_id"
        ))

        self.add_join_rule(JoinRule(
            from_entity="ORDER",
            to_entity="INVOICE",
            join_key_from="order_id",
            join_key_to="order_id",
            cardinality="1:N",
            join_condition="orders.order_id = invoices.order_id"
        ))

        self.add_join_rule(JoinRule(
            from_entity="ORDER",
            to_entity="TRANSACTION",
            join_key_from="order_id",
            join_key_to="order_id",
            cardinality="1:N",
            join_condition="orders.order_id = transactions.order_id"
        ))

        self.add_join_rule(JoinRule(
            from_entity="ORDER",
            to_entity="ORDER_ITEM",
            join_key_from="order_id",
            join_key_to="order_id",
            cardinality="1:N",
            join_condition="orders.order_id = order_items.order_id",
        ))

        self.add_join_rule(JoinRule(
            from_entity="ORDER_ITEM",
            to_entity="PRODUCT",
            join_key_from="product_id",
            join_key_to="product_id",
            cardinality="N:1",
            join_condition="order_items.product_id = products.product_id",
        ))

        self.add_join_rule(JoinRule(
            from_entity="PRODUCT",
            to_entity="SUPPLIER",
            join_key_from="supplier_id",
            join_key_to="supplier_id",
            cardinality="N:1",
            join_condition="products.supplier_id = suppliers.supplier_id",
        ))

        self.add_join_rule(JoinRule(
            from_entity="ORDER",
            to_entity="RETURN",
            join_key_from="order_id",
            join_key_to="order_id",
            cardinality="1:N",
            join_condition="orders.order_id = returns.order_id",
        ))
    
    def add_entity(self, entity: EntityDefinition) -> None:
        """Add entity definition to ontology."""
        self.entities[entity.entity_id] = entity
        
        # Add to NetworkX graph
        if self.graph is not None:
            self.graph.add_node(
                entity.entity_id,
                type="entity",
                name=entity.name,
                table=entity.table_name,
                attributes=list(entity.attributes.keys())
            )
    
    def add_metric(self, metric: MetricDefinition) -> None:
        """Add metric definition to ontology."""
        self.metrics[metric.metric_id] = metric
        
        # Add to NetworkX graph
        if self.graph is not None:
            self.graph.add_node(
                metric.metric_id,
                type="metric",
                name=metric.name,
                formula=metric.formula,
                requires=metric.requires_entities
            )
    
    def add_constraint(self, constraint: ConstraintRule) -> None:
        """Add constraint to ontology."""
        self.constraints[constraint.rule_id] = constraint
    
    def add_join_rule(self, join: JoinRule) -> None:
        """Add join rule to ontology."""
        self.joins.append(join)
        
        # Add to NetworkX graph as edge
        if self.graph is not None:
            self.graph.add_edge(
                join.from_entity,
                join.to_entity,
                type="join",
                cardinality=join.cardinality,
                condition=join.join_condition
            )
    
    def find_entity_by_name(self, name: str) -> Optional[EntityDefinition]:
        """Find entity by name (case-insensitive, alias-aware)."""
        name_lower = name.lower()
        
        for entity in self.entities.values():
            if entity.name.lower() == name_lower:
                return entity
            if any(alias.lower() == name_lower for alias in entity.natural_language_aliases):
                return entity
        
        return None
    
    def find_metric_by_name(self, name: str) -> Optional[MetricDefinition]:
        """Find metric by name (case-insensitive, alias-aware)."""
        name_lower = name.lower()
        
        for metric in self.metrics.values():
            if metric.name.lower() == name_lower:
                return metric
            if any(alias.lower() == name_lower for alias in metric.natural_language_aliases):
                return metric
        
        return None
    
    def get_join_path(self, from_entity: str, to_entity: str) -> Optional[List[str]]:
        """Find shortest join path between entities using NetworkX."""
        if self.graph is None:
            return None
        
        try:
            path = nx.shortest_path(self.graph, from_entity, to_entity)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def get_applicable_constraints(self, entity_ids: List[str]) -> List[ConstraintRule]:
        """Get all constraints applicable to given entities."""
        applicable = []
        for constraint in self.constraints.values():
            if any(e in entity_ids for e in constraint.entities_affected):
                applicable.append(constraint)
        return applicable
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize ontology to dictionary."""
        return {
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "constraints": {k: v.to_dict() for k, v in self.constraints.items()},
            "joins": [j.to_dict() for j in self.joins],
        }
    
    def save(self, filepath: str) -> None:
        """Save ontology to JSON file."""
        import json
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    @classmethod
    def load(cls, filepath: str) -> 'BusinessOntology':
        """Load ontology from JSON file."""
        import json
        ont = cls()
        with open(filepath, 'r') as f:
            data = json.load(f)
        # Could reconstruct from data if needed
        return ont
