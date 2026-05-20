"""
Database management layer with PostgreSQL support and synthetic data generation.

Supports 3 complete databases with ~5,000 realistic records each:
- Sales Database: Customers, Orders, Invoices, Transactions
- Inventory Database: Products, Stock Levels, Reorder History
- Analytics Database: Aggregated metrics, time-series data
"""

import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3
import os

import sqlalchemy as sa
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, String, Float, Integer, DateTime, Boolean, JSON
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


# ============================================================================
# Database Configuration & Schemas
# ============================================================================


@dataclass
class DatabaseConfig:
    """Configuration for database connection."""
    engine_type: str = os.getenv("DB_DIALECT", "sqlite")  # "postgresql", "sqlite", "memory"
    host: Optional[str] = os.getenv("DB_HOST", "localhost")
    port: Optional[int] = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "sales")
    user: Optional[str] = os.getenv("DB_USER", "postgres")
    password: Optional[str] = os.getenv("DB_PASSWORD", "postgres")
    echo: bool = False

    @property
    def dialect(self) -> str:
        """Return SQL dialect string."""
        return "postgresql" if self.engine_type == "postgresql" else "sqlite"


def get_connection_string(config: DatabaseConfig) -> str:
    """Build connection string from config."""
    if config.engine_type == "sqlite":
        return f"sqlite:///{config.database}.db"
    elif config.engine_type == "memory":
        return "sqlite:///:memory:"
    elif config.engine_type == "postgresql":
        user_pass = f"{config.user}:{config.password}@" if config.user else ""
        return f"postgresql://{user_pass}{config.host}:{config.port}/{config.database}"
    else:
        raise ValueError(f"Unsupported engine type: {config.engine_type}")


# ============================================================================
# Synthetic Data Generator
# ============================================================================


class SyntheticDataGenerator:
    """Generates realistic synthetic data for 3 complete databases."""
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.regions = ["North America", "Europe", "Asia Pacific", "Latin America"]
        self.departments = ["Sales", "Marketing", "Operations", "Finance", "IT"]
        self.product_categories = [
            "Electronics", "Clothing", "Home & Garden", "Sports", "Books",
            "Food & Beverages", "Health & Beauty", "Toys", "Furniture"
        ]
        
    def generate_sales_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate Sales database data: all tables including new ones."""
        customers = self._generate_customers(50_000)
        products = self._generate_products(10_000)
        suppliers = self._generate_suppliers(500)
        orders = self._generate_orders(customers, products, 300_000)
        order_items = self._generate_order_items(orders, products, 800_000)
        invoices = self._generate_invoices(orders, 180_000)
        transactions = self._generate_transactions(orders, 600_000)
        returns = self._generate_returns(orders, customers, products, 30_000)

        return {
            "customers": customers,
            "products": products,
            "suppliers": suppliers,
            "orders": orders,
            "order_items": order_items,
            "invoices": invoices,
            "transactions": transactions,
            "returns": returns,
        }
    
    def generate_inventory_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate Inventory database data: Products, Stock Levels, Reorder History."""
        products = self._generate_products(10_000)
        stock_levels = self._generate_stock_levels(products)
        reorder_history = self._generate_reorder_history(products, 150_000)
        
        return {
            "products": products,
            "stock_levels": stock_levels,
            "reorder_history": reorder_history,
        }
    
    def generate_analytics_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate Analytics database data: Aggregated metrics, time-series."""
        daily_metrics = self._generate_daily_metrics(1825)
        cohort_metrics = self._generate_cohort_metrics(3_000)
        product_analytics = self._generate_product_analytics(10_000)
        
        return {
            "daily_metrics": daily_metrics,
            "cohort_metrics": cohort_metrics,
            "product_analytics": product_analytics,
        }
    
    def _generate_customers(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic customer records."""
        customers = []
        for i in range(count):
            customer_id = f"CUST_{i+1:06d}"
            created_date = datetime.utcnow() - timedelta(days=random.randint(1, 1095))
            total_spent = round(random.uniform(100, 50000), 2)
            
            customers.append({
                "customer_id": customer_id,
                "name": f"Customer {i+1}",
                "email": f"customer_{i+1}@example.com",
                "region": random.choice(self.regions),
                "department": random.choice(self.departments),
                "created_date": created_date,
                "total_spent": total_spent,
                "order_count": random.randint(1, 100),
                "last_order_date": (created_date + timedelta(days=random.randint(1, 365))),
                "customer_tier": random.choice(["Bronze", "Silver", "Gold", "Platinum"]),
            })
        return customers
    
    def _generate_products(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic product records."""
        products = []
        for i in range(count):
            product_id = f"PROD_{i+1:06d}"
            base_price = round(random.uniform(10, 500), 2)
            
            products.append({
                "product_id": product_id,
                "name": f"Product {i+1}",
                "category": random.choice(self.product_categories),
                "price": base_price,
                "cost": round(base_price * random.uniform(0.3, 0.7), 2),
                "description": f"High-quality product in category",
                "stock_quantity": random.randint(0, 10000),
                "reorder_level": random.randint(100, 1000),
                "supplier_id": f"SUP_{random.randint(1, 50):03d}",
                "created_date": (datetime.utcnow() - timedelta(days=random.randint(1, 1095))),
                "is_active": random.choice([True, True, True, False]),
            })
        return products
    
    def _generate_orders(
        self,
        customers: List[Dict[str, Any]],
        products: List[Dict[str, Any]],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate realistic order records."""
        orders = []
        for i in range(count):
            order_id = f"ORD_{i+1:07d}"
            customer = random.choice(customers)
            order_date = datetime.utcnow() - timedelta(days=random.randint(1, 730))
            
            # Random order items (1-5 items per order)
            items = random.randint(1, 5)
            total_amount = 0
            for _ in range(items):
                product = random.choice(products)
                qty = random.randint(1, 10)
                total_amount += product["price"] * qty
            
            total_amount = round(total_amount, 2)
            
            orders.append({
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "order_date": order_date,
                "total_amount": total_amount,
                "item_count": items,
                "status": random.choice(["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]),
                "shipping_address": f"{customer['region']}, Address",
                "shipping_cost": round(random.uniform(5, 100), 2),
                "tax_amount": round(total_amount * 0.1, 2),
            })
        return orders
    
    def _generate_invoices(
        self,
        orders: List[Dict[str, Any]],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate realistic invoice records."""
        invoices = []
        selected_orders = random.sample(orders, min(count, len(orders)))
        
        for i, order in enumerate(selected_orders):
            invoice_id = f"INV_{i+1:07d}"
            invoice_date = order["order_date"]
            due_date = invoice_date + timedelta(days=30)
            
            invoices.append({
                "invoice_id": invoice_id,
                "order_id": order["order_id"],
                "customer_id": order["customer_id"],
                "invoice_date": invoice_date,
                "due_date": due_date,
                "subtotal": round(order["total_amount"] - order["tax_amount"], 2),
                "tax_amount": order["tax_amount"],
                "total_amount": order["total_amount"],
                "status": random.choice(["Draft", "Issued", "Paid", "Overdue", "Cancelled"]),
                "payment_method": random.choice(["Credit Card", "Bank Transfer", "PayPal", "Check"]),
                "notes": "Invoice for order processing",
            })
        return invoices
    
    def _generate_transactions(
        self,
        orders: List[Dict[str, Any]],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate realistic transaction records."""
        transactions = []
        for i in range(count):
            transaction_id = f"TXN_{i+1:09d}"
            order = random.choice(orders)
            transaction_date = order["order_date"]
            
            transactions.append({
                "transaction_id": transaction_id,
                "order_id": order["order_id"],
                "customer_id": order["customer_id"],
                "transaction_date": transaction_date,
                "transaction_type": random.choice(["Sale", "Return", "Refund", "Exchange"]),
                "amount": order["total_amount"],
                "status": random.choice(["Completed", "Pending", "Failed"]),
                "payment_gateway": random.choice(["Stripe", "PayPal", "Square"]),
                "metadata": json.dumps({"ip_address": f"192.168.{random.randint(1,255)}.{random.randint(1,255)}"}),
            })
        return transactions
    
    def _generate_suppliers(self, count: int) -> List[Dict[str, Any]]:
        """Generate supplier records."""
        countries = ["USA", "China", "Germany", "India", "UK", "Japan", "Canada", "Australia"]
        suppliers = []
        for i in range(count):
            suppliers.append({
                "supplier_id": f"SUP_{i+1:03d}",
                "name": f"Supplier {i+1} Corp",
                "country": random.choice(countries),
                "category": random.choice(self.product_categories),
                "contact_email": f"supplier{i+1}@supply.com",
                "lead_time_days": random.randint(3, 60),
                "rating": round(random.uniform(2.5, 5.0), 2),
                "is_active": random.choice([True, True, True, False]),
            })
        return suppliers

    def _generate_order_items(
        self,
        orders: List[Dict[str, Any]],
        products: List[Dict[str, Any]],
        count: int,
    ) -> List[Dict[str, Any]]:
        """Generate order_items records."""
        items = []
        order_ids = [o["order_id"] for o in orders]
        prod_map = {p["product_id"]: p for p in products}
        for i in range(count):
            order_id = random.choice(order_ids)
            product = random.choice(products)
            qty = random.randint(1, 10)
            unit_price = round(product["price"], 2)
            discount_pct = round(random.uniform(0, 0.25), 4)
            line_total = round(unit_price * qty * (1 - discount_pct), 2)
            items.append({
                "order_item_id": f"OI_{i+1:08d}",
                "order_id": order_id,
                "product_id": product["product_id"],
                "quantity": qty,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "line_total": line_total,
            })
        return items

    def _generate_returns(
        self,
        orders: List[Dict[str, Any]],
        customers: List[Dict[str, Any]],
        products: List[Dict[str, Any]],
        count: int,
    ) -> List[Dict[str, Any]]:
        """Generate returns records."""
        reasons = ["Defective", "Wrong item", "Changed mind", "Better price elsewhere", "Damaged in shipping"]
        delivered = [o for o in orders if o["status"] == "Delivered"]
        if not delivered:
            delivered = orders
        returns = []
        for i in range(count):
            order = random.choice(delivered)
            product = random.choice(products)
            return_date = order["order_date"] + timedelta(days=random.randint(1, 30))
            returns.append({
                "return_id": f"RET_{i+1:06d}",
                "order_id": order["order_id"],
                "customer_id": order["customer_id"],
                "product_id": product["product_id"],
                "return_date": return_date,
                "reason": random.choice(reasons),
                "amount": round(order["total_amount"] * random.uniform(0.1, 1.0), 2),
                "status": random.choice(["Pending", "Approved", "Completed", "Rejected"]),
            })
        return returns

    def _generate_stock_levels(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate stock level records."""
        stock_levels = []
        for product in products:
            stock_levels.append({
                "product_id": product["product_id"],
                "warehouse": random.choice(["Warehouse A", "Warehouse B", "Warehouse C", "Distribution Center"]),
                "quantity_on_hand": random.randint(0, 5000),
                "quantity_reserved": random.randint(0, 1000),
                "quantity_available": random.randint(0, 5000),
                "last_count_date": (datetime.utcnow() - timedelta(days=random.randint(1, 90))),
            })
        return stock_levels
    
    def _generate_reorder_history(
        self,
        products: List[Dict[str, Any]],
        count: int
    ) -> List[Dict[str, Any]]:
        """Generate reorder history."""
        reorder_history = []
        for i in range(count):
            product = random.choice(products)
            reorder_date = datetime.utcnow() - timedelta(days=random.randint(1, 365))
            
            reorder_history.append({
                "reorder_id": f"RO_{i+1:07d}",
                "product_id": product["product_id"],
                "reorder_date": reorder_date,
                "quantity_ordered": random.randint(100, 5000),
                "supplier_id": product["supplier_id"],
                "expected_delivery_date": (reorder_date + timedelta(days=random.randint(5, 30))),
                "actual_delivery_date": (reorder_date + timedelta(days=random.randint(5, 35))),
                "cost_per_unit": round(product["cost"], 2),
                "total_cost": round(product["cost"] * random.randint(100, 5000), 2),
            })
        return reorder_history
    
    def _generate_daily_metrics(self, days: int) -> List[Dict[str, Any]]:
        """Generate daily metrics for analytics."""
        daily_metrics = []
        base_revenue = 10000
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=days - i)
            daily_metrics.append({
                "date": date.date(),
                "total_orders": random.randint(50, 500),
                "total_revenue": round(base_revenue + random.uniform(-5000, 10000), 2),
                "total_customers": random.randint(20, 200),
                "avg_order_value": round(random.uniform(100, 500), 2),
                "new_customers": random.randint(5, 50),
                "returning_customers": random.randint(10, 150),
                "conversion_rate": round(random.uniform(0.01, 0.1), 4),
            })
        return daily_metrics
    
    def _generate_cohort_metrics(self, cohorts: int) -> List[Dict[str, Any]]:
        """Generate cohort analysis data."""
        cohort_metrics = []
        for i in range(cohorts):
            cohort_date = datetime.utcnow() - timedelta(days=random.randint(1, 1095))
            
            cohort_metrics.append({
                "cohort_id": f"COHORT_{i+1:04d}",
                "cohort_date": cohort_date.date(),
                "cohort_size": random.randint(100, 5000),
                "retention_week_1": round(random.uniform(0.5, 0.95), 3),
                "retention_week_4": round(random.uniform(0.2, 0.8), 3),
                "retention_week_12": round(random.uniform(0.1, 0.6), 3),
                "avg_ltv": round(random.uniform(500, 5000), 2),
                "churn_rate": round(random.uniform(0.01, 0.2), 3),
            })
        return cohort_metrics
    
    def _generate_product_analytics(self, products: int) -> List[Dict[str, Any]]:
        """Generate product-level analytics."""
        product_analytics = []
        for i in range(products):
            product_analytics.append({
                "product_id": f"PROD_{i+1:06d}",
                "total_units_sold": random.randint(0, 10000),
                "total_revenue": round(random.uniform(0, 500000), 2),
                "avg_rating": round(random.uniform(1, 5), 2),
                "review_count": random.randint(0, 1000),
                "return_rate": round(random.uniform(0, 0.2), 3),
                "views": random.randint(0, 100000),
                "page_conversion_rate": round(random.uniform(0, 0.1), 3),
            })
        return product_analytics

    # ── HR generators ─────────────────────────────────────────────────────────

    def generate_hr_data(self) -> Dict[str, List[Dict[str, Any]]]:
        employees    = self._generate_employees(20_000)
        departments  = self._generate_hr_departments(50)
        salaries     = self._generate_salaries(employees, years=[2022, 2023, 2024])
        reviews      = self._generate_performance_reviews(employees, 80_000)
        leaves       = self._generate_leave_records(employees, 50_000)
        return {
            "employees": employees,
            "departments": departments,
            "salaries": salaries,
            "performance_reviews": reviews,
            "leave_records": leaves,
        }

    def _generate_employees(self, count: int) -> List[Dict[str, Any]]:
        titles = ["Engineer", "Manager", "Analyst", "Director", "Associate",
                  "Specialist", "Coordinator", "Lead", "VP", "Intern"]
        employees = []
        for i in range(count):
            hire_date = datetime.utcnow() - timedelta(days=random.randint(30, 3650))
            employees.append({
                "employee_id": f"EMP_{i+1:06d}",
                "name": f"Employee {i+1}",
                "email": f"emp_{i+1}@company.com",
                "department": random.choice(self.departments),
                "job_title": random.choice(titles),
                "region": random.choice(self.regions),
                "hire_date": hire_date,
                "salary": round(random.uniform(30_000, 200_000), 2),
                "performance_score": round(random.uniform(1.0, 5.0), 2),
                "manager_id": f"EMP_{random.randint(1, max(1, count//10)):06d}",
                "is_active": random.choices([True, False], weights=[90, 10])[0],
            })
        return employees

    def _generate_hr_departments(self, count: int) -> List[Dict[str, Any]]:
        dept_names = self.departments[:count] if count <= len(self.departments) else \
            self.departments + [f"Dept_{i}" for i in range(count - len(self.departments))]
        depts = []
        for i, name in enumerate(dept_names):
            depts.append({
                "dept_id": f"DEPT_{i+1:03d}",
                "name": name,
                "region": random.choice(self.regions),
                "headcount": random.randint(10, 500),
                "annual_budget": round(random.uniform(500_000, 10_000_000), 2),
                "manager_id": f"EMP_{random.randint(1, 200):06d}",
            })
        return depts

    def _generate_salaries(self, employees: List[Dict], years: List[int]) -> List[Dict[str, Any]]:
        salaries = []
        sid = 0
        for emp in employees:
            for year in years:
                base = round(emp["salary"] * random.uniform(0.85, 1.0), 2)
                bonus = round(base * random.uniform(0, 0.25), 2)
                sid += 1
                salaries.append({
                    "salary_id": f"SAL_{sid:08d}",
                    "employee_id": emp["employee_id"],
                    "year": year,
                    "base_salary": base,
                    "bonus": bonus,
                    "total_compensation": round(base + bonus, 2),
                })
        return salaries

    def _generate_performance_reviews(self, employees: List[Dict], count: int) -> List[Dict[str, Any]]:
        ratings = ["Exceeds Expectations", "Meets Expectations", "Needs Improvement",
                   "Outstanding", "Below Expectations"]
        reviews = []
        emp_ids = [e["employee_id"] for e in employees]
        for i in range(count):
            score = round(random.uniform(1.0, 5.0), 2)
            reviews.append({
                "review_id": f"REV_{i+1:08d}",
                "employee_id": random.choice(emp_ids),
                "quarter": random.choice(["Q1", "Q2", "Q3", "Q4"]),
                "year": random.randint(2022, 2024),
                "score": score,
                "rating": ratings[min(int((5 - score) / 1.2), len(ratings) - 1)],
                "reviewer_id": random.choice(emp_ids),
            })
        return reviews

    def _generate_leave_records(self, employees: List[Dict], count: int) -> List[Dict[str, Any]]:
        leave_types = ["Annual Leave", "Sick Leave", "Maternity Leave",
                       "Paternity Leave", "Unpaid Leave", "Study Leave"]
        emp_ids = [e["employee_id"] for e in employees]
        records = []
        for i in range(count):
            start = datetime.utcnow() - timedelta(days=random.randint(1, 730))
            days = random.randint(1, 20)
            records.append({
                "leave_id": f"LV_{i+1:07d}",
                "employee_id": random.choice(emp_ids),
                "leave_type": random.choice(leave_types),
                "start_date": start,
                "end_date": start + timedelta(days=days),
                "days_taken": days,
                "status": random.choice(["Approved", "Pending", "Rejected"]),
            })
        return records

    # ── Finance generators ────────────────────────────────────────────────────

    def generate_finance_data(self) -> Dict[str, List[Dict[str, Any]]]:
        accounts = self._generate_accounts(1_000)
        budget   = self._generate_budget_items(5_000)
        expenses = self._generate_expenses(accounts, 100_000)
        forecasts = self._generate_forecasts(2_000)
        return {
            "accounts": accounts,
            "budget_items": budget,
            "expenses": expenses,
            "forecasts": forecasts,
        }

    def _generate_accounts(self, count: int) -> List[Dict[str, Any]]:
        acct_types = ["Asset", "Liability", "Revenue", "Expense", "Equity"]
        currencies = ["USD", "EUR", "GBP", "JPY", "AUD"]
        accounts = []
        for i in range(count):
            accounts.append({
                "account_id": f"ACC_{i+1:05d}",
                "name": f"Account {i+1}",
                "account_type": random.choice(acct_types),
                "balance": round(random.uniform(-500_000, 5_000_000), 2),
                "currency": random.choice(currencies),
                "department": random.choice(self.departments),
                "created_date": datetime.utcnow() - timedelta(days=random.randint(365, 3650)),
            })
        return accounts

    def _generate_budget_items(self, count: int) -> List[Dict[str, Any]]:
        categories = ["Headcount", "Marketing", "Infrastructure", "R&D",
                      "Travel", "Software", "Training", "Operations"]
        items = []
        for i in range(count):
            allocated = round(random.uniform(10_000, 2_000_000), 2)
            spent_pct = random.uniform(0.4, 1.3)
            spent = round(allocated * spent_pct, 2)
            items.append({
                "budget_id": f"BUD_{i+1:06d}",
                "department": random.choice(self.departments),
                "category": random.choice(categories),
                "year": random.randint(2022, 2024),
                "quarter": random.choice(["Q1", "Q2", "Q3", "Q4"]),
                "allocated": allocated,
                "spent": spent,
                "variance": round(allocated - spent, 2),
            })
        return items

    def _generate_expenses(self, accounts: List[Dict], count: int) -> List[Dict[str, Any]]:
        categories = ["Software", "Travel", "Hardware", "Consulting",
                      "Marketing", "Utilities", "Rent", "Salaries"]
        acct_ids = [a["account_id"] for a in accounts]
        expenses = []
        for i in range(count):
            expenses.append({
                "expense_id": f"EXP_{i+1:08d}",
                "account_id": random.choice(acct_ids),
                "department": random.choice(self.departments),
                "category": random.choice(categories),
                "amount": round(random.uniform(50, 50_000), 2),
                "expense_date": datetime.utcnow() - timedelta(days=random.randint(1, 730)),
                "status": random.choice(["Approved", "Pending", "Rejected", "Paid"]),
                "description": f"Expense for {random.choice(categories).lower()} services",
            })
        return expenses

    def _generate_forecasts(self, count: int) -> List[Dict[str, Any]]:
        metrics = ["Revenue", "Expenses", "Headcount", "Churn Rate",
                   "Customer Acquisition", "Gross Margin", "EBITDA"]
        models = ["Linear Regression", "ARIMA", "Prophet", "XGBoost", "Naive Baseline"]
        forecasts = []
        for i in range(count):
            predicted = round(random.uniform(10_000, 5_000_000), 2)
            actual = round(predicted * random.uniform(0.7, 1.3), 2)
            forecasts.append({
                "forecast_id": f"FCT_{i+1:06d}",
                "metric": random.choice(metrics),
                "period": f"2024-Q{random.randint(1,4)}",
                "predicted_value": predicted,
                "actual_value": actual,
                "model": random.choice(models),
                "accuracy_pct": round(100 - abs(predicted - actual) / max(predicted, 1) * 100, 2),
            })
        return forecasts


# ============================================================================
# Database Manager
# ============================================================================


class DatabaseManager:
    """Manages database connections, schema creation, and data operations."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        connection_string = get_connection_string(config)
        
        # Use StaticPool for in-memory databases
        if config.engine_type == "memory":
            self.engine = create_engine(
                connection_string,
                echo=config.echo,
                poolclass=StaticPool,
            )
        else:
            self.engine = create_engine(
                connection_string,
                echo=config.echo,
                pool_pre_ping=True,
            )
        
        self.metadata = MetaData()
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_sales_schema(self) -> None:
        """Create Sales database schema."""
        # Drop existing tables if they exist
        with self.engine.begin() as connection:
            self.metadata.reflect(bind=self.engine)
            self.metadata.drop_all(self.engine)
            self.metadata.clear()
        
        # Create tables
        customers_table = Table(
            "customers",
            self.metadata,
            Column("customer_id", String(50), primary_key=True),
            Column("name", String(255)),
            Column("email", String(255)),
            Column("region", String(100)),
            Column("department", String(100)),
            Column("created_date", DateTime),
            Column("total_spent", Float),
            Column("order_count", Integer),
            Column("last_order_date", DateTime),
            Column("customer_tier", String(50)),
        )
        
        products_table = Table(
            "products",
            self.metadata,
            Column("product_id", String(50), primary_key=True),
            Column("name", String(255)),
            Column("category", String(100)),
            Column("price", Float),
            Column("cost", Float),
            Column("description", String(500)),
            Column("stock_quantity", Integer),
            Column("reorder_level", Integer),
            Column("supplier_id", String(50)),
            Column("created_date", DateTime),
            Column("is_active", Boolean),
        )
        
        orders_table = Table(
            "orders",
            self.metadata,
            Column("order_id", String(50), primary_key=True),
            Column("customer_id", String(50)),
            Column("order_date", DateTime),
            Column("total_amount", Float),
            Column("item_count", Integer),
            Column("status", String(50)),
            Column("shipping_address", String(255)),
            Column("shipping_cost", Float),
            Column("tax_amount", Float),
        )
        
        invoices_table = Table(
            "invoices",
            self.metadata,
            Column("invoice_id", String(50), primary_key=True),
            Column("order_id", String(50)),
            Column("customer_id", String(50)),
            Column("invoice_date", DateTime),
            Column("due_date", DateTime),
            Column("subtotal", Float),
            Column("tax_amount", Float),
            Column("total_amount", Float),
            Column("status", String(50)),
            Column("payment_method", String(100)),
            Column("notes", String(500)),
        )
        
        transactions_table = Table(
            "transactions",
            self.metadata,
            Column("transaction_id", String(50), primary_key=True),
            Column("order_id", String(50)),
            Column("customer_id", String(50)),
            Column("transaction_date", DateTime),
            Column("transaction_type", String(50)),
            Column("amount", Float),
            Column("status", String(50)),
            Column("payment_gateway", String(100)),
            Column("metadata", JSON),
        )

        Table(
            "suppliers",
            self.metadata,
            Column("supplier_id", String(50), primary_key=True),
            Column("name", String(255)),
            Column("country", String(100)),
            Column("category", String(100)),
            Column("contact_email", String(255)),
            Column("lead_time_days", Integer),
            Column("rating", Float),
            Column("is_active", Boolean),
        )

        Table(
            "order_items",
            self.metadata,
            Column("order_item_id", String(50), primary_key=True),
            Column("order_id", String(50)),
            Column("product_id", String(50)),
            Column("quantity", Integer),
            Column("unit_price", Float),
            Column("discount_pct", Float),
            Column("line_total", Float),
        )

        Table(
            "returns",
            self.metadata,
            Column("return_id", String(50), primary_key=True),
            Column("order_id", String(50)),
            Column("customer_id", String(50)),
            Column("product_id", String(50)),
            Column("return_date", DateTime),
            Column("reason", String(255)),
            Column("amount", Float),
            Column("status", String(50)),
        )

        stock_levels_table = Table(
            "stock_levels",
            self.metadata,
            Column("product_id", String(50), primary_key=True),
            Column("warehouse", String(100)),
            Column("quantity_on_hand", Integer),
            Column("quantity_reserved", Integer),
            Column("quantity_available", Integer),
            Column("last_count_date", DateTime),
        )
        
        reorder_history_table = Table(
            "reorder_history",
            self.metadata,
            Column("reorder_id", String(50), primary_key=True),
            Column("product_id", String(50)),
            Column("reorder_date", DateTime),
            Column("quantity_ordered", Integer),
            Column("supplier_id", String(50)),
            Column("expected_delivery_date", DateTime),
            Column("actual_delivery_date", DateTime),
            Column("cost_per_unit", Float),
            Column("total_cost", Float),
        )
        
        daily_metrics_table = Table(
            "daily_metrics",
            self.metadata,
            Column("date", String(20), primary_key=True),
            Column("total_orders", Integer),
            Column("total_revenue", Float),
            Column("total_customers", Integer),
            Column("avg_order_value", Float),
            Column("new_customers", Integer),
            Column("returning_customers", Integer),
            Column("conversion_rate", Float),
        )
        
        cohort_metrics_table = Table(
            "cohort_metrics",
            self.metadata,
            Column("cohort_id", String(50), primary_key=True),
            Column("cohort_date", String(20)),
            Column("cohort_size", Integer),
            Column("retention_week_1", Float),
            Column("retention_week_4", Float),
            Column("retention_week_12", Float),
            Column("avg_ltv", Float),
            Column("churn_rate", Float),
        )
        
        product_analytics_table = Table(
            "product_analytics",
            self.metadata,
            Column("product_id", String(50), primary_key=True),
            Column("total_units_sold", Integer),
            Column("total_revenue", Float),
            Column("avg_rating", Float),
            Column("review_count", Integer),
            Column("return_rate", Float),
            Column("views", Integer),
            Column("page_conversion_rate", Float),
        )
        
        # ── HR tables ─────────────────────────────────────────────────────────
        Table(
            "employees",
            self.metadata,
            Column("employee_id", String(50), primary_key=True),
            Column("name", String(255)),
            Column("email", String(255)),
            Column("department", String(100)),
            Column("job_title", String(100)),
            Column("region", String(100)),
            Column("hire_date", DateTime),
            Column("salary", Float),
            Column("performance_score", Float),
            Column("manager_id", String(50)),
            Column("is_active", Boolean),
        )
        Table(
            "departments",
            self.metadata,
            Column("dept_id", String(50), primary_key=True),
            Column("name", String(100)),
            Column("region", String(100)),
            Column("headcount", Integer),
            Column("annual_budget", Float),
            Column("manager_id", String(50)),
        )
        Table(
            "salaries",
            self.metadata,
            Column("salary_id", String(50), primary_key=True),
            Column("employee_id", String(50)),
            Column("year", Integer),
            Column("base_salary", Float),
            Column("bonus", Float),
            Column("total_compensation", Float),
        )
        Table(
            "performance_reviews",
            self.metadata,
            Column("review_id", String(50), primary_key=True),
            Column("employee_id", String(50)),
            Column("quarter", String(10)),
            Column("year", Integer),
            Column("score", Float),
            Column("rating", String(50)),
            Column("reviewer_id", String(50)),
        )
        Table(
            "leave_records",
            self.metadata,
            Column("leave_id", String(50), primary_key=True),
            Column("employee_id", String(50)),
            Column("leave_type", String(50)),
            Column("start_date", DateTime),
            Column("end_date", DateTime),
            Column("days_taken", Integer),
            Column("status", String(50)),
        )

        # ── Finance tables ────────────────────────────────────────────────────
        Table(
            "accounts",
            self.metadata,
            Column("account_id", String(50), primary_key=True),
            Column("name", String(255)),
            Column("account_type", String(100)),
            Column("balance", Float),
            Column("currency", String(10)),
            Column("department", String(100)),
            Column("created_date", DateTime),
        )
        Table(
            "budget_items",
            self.metadata,
            Column("budget_id", String(50), primary_key=True),
            Column("department", String(100)),
            Column("category", String(100)),
            Column("year", Integer),
            Column("quarter", String(10)),
            Column("allocated", Float),
            Column("spent", Float),
            Column("variance", Float),
        )
        Table(
            "expenses",
            self.metadata,
            Column("expense_id", String(50), primary_key=True),
            Column("account_id", String(50)),
            Column("department", String(100)),
            Column("category", String(100)),
            Column("amount", Float),
            Column("expense_date", DateTime),
            Column("status", String(50)),
            Column("description", String(500)),
        )
        Table(
            "forecasts",
            self.metadata,
            Column("forecast_id", String(50), primary_key=True),
            Column("metric", String(100)),
            Column("period", String(20)),
            Column("predicted_value", Float),
            Column("actual_value", Float),
            Column("model", String(100)),
            Column("accuracy_pct", Float),
        )

        self.metadata.create_all(self.engine)

    def create_full_schema(self) -> None:
        """Alias for create_sales_schema — creates all tables including new ones."""
        self.create_sales_schema()

    def insert_data(self, table_name: str, records: List[Dict[str, Any]], chunk_size: int = 5_000) -> int:
        """Insert records into table in chunks. Returns count inserted."""
        if not records:
            return 0

        stmt = sa.insert(sa.table(table_name, *[sa.column(k) for k in records[0].keys()]))
        total = 0
        try:
            with self.engine.begin() as connection:
                for i in range(0, len(records), chunk_size):
                    chunk = records[i:i + chunk_size]
                    result = connection.execute(stmt, chunk)
                    total += result.rowcount
        except Exception as e:
            print(f"Error inserting into {table_name}: {e}")
        return total
    
    def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query and return results as list of dicts."""
        with self.engine.connect() as connection:
            result = connection.execute(sa.text(sql), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Alias for query() — used by orchestrator."""
        return self.query(sql, params)

    def get_schema(self) -> Dict[str, Dict[str, str]]:
        """Get schema information for all tables."""
        inspector = inspect(self.engine)
        schema_info = {}
        
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            schema_info[table_name] = {
                col["name"]: str(col["type"]) for col in columns
            }
        
        return schema_info
    
    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()


# ============================================================================
# Database Initialization Helper
# ============================================================================


def _create_pg_databases(host: str, port: int, user: str, password: str, db_names: list) -> None:
    """Create PostgreSQL databases if they don't exist (connects via 'postgres' default DB)."""
    import sqlalchemy as _sa
    admin_url = f"postgresql://{user}:{password}@{host}:{port}/postgres"
    engine = _sa.create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        existing = {row[0] for row in conn.execute(_sa.text("SELECT datname FROM pg_database"))}
        for db_name in db_names:
            if db_name not in existing:
                conn.execute(_sa.text(f'CREATE DATABASE "{db_name}"'))
                print(f"  Created database: {db_name}")
            else:
                print(f"  Database already exists: {db_name}")
    engine.dispose()


def initialize_databases(
    use_postgresql: bool = False,
    postgres_host: str = None,
    postgres_user: str = None,
    postgres_password: str = None,
):
    """Initialize all 5 databases with synthetic data."""
    engine_type = (
        "postgresql"
        if use_postgresql
        else os.getenv("DB_DIALECT", "sqlite")
    )
    host = postgres_host or os.getenv("DB_HOST", "localhost")
    user = postgres_user or os.getenv("DB_USER", "postgres")
    password = postgres_password or os.getenv("DB_PASSWORD", "postgres")

    if engine_type == "postgresql":
        port = int(os.getenv("DB_PORT", "5432"))
        _create_pg_databases(host, port, user, password, [
            "nlretrieval_sales", "nlretrieval_inventory",
            "nlretrieval_analytics", "nlretrieval_hr", "nlretrieval_finance",
        ])

    generator = SyntheticDataGenerator(seed=42)

    def _make_config(db_name: str) -> DatabaseConfig:
        return DatabaseConfig(
            engine_type=engine_type,
            host=host if engine_type == "postgresql" else None,
            user=user if engine_type == "postgresql" else None,
            password=password if engine_type == "postgresql" else None,
            database=f"nlretrieval_{db_name}" if engine_type == "postgresql" else db_name,
        )

    managers = {}

    for db_name, data_fn in [
        ("sales",     generator.generate_sales_data),
        ("inventory", generator.generate_inventory_data),
        ("analytics", generator.generate_analytics_data),
        ("hr",        generator.generate_hr_data),
        ("finance",   generator.generate_finance_data),
    ]:
        print(f"Initializing {db_name.title()} database...")
        mgr = DatabaseManager(_make_config(db_name))
        mgr.create_full_schema()
        for table_name, records in data_fn().items():
            count = mgr.insert_data(table_name, records)
            print(f"  - Inserted {count} records into {table_name}")
        managers[db_name] = mgr

    return (managers["sales"], managers["inventory"], managers["analytics"],
            managers["hr"], managers["finance"])
