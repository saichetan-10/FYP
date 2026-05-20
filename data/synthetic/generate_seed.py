#!/usr/bin/env python3
"""
Generates seed_data.sql — full PostgreSQL DDL + batched INSERTs (~2 M rows).

Usage:
    python data/synthetic/generate_seed.py

Then load into PostgreSQL:
    createdb nlretrieval_sales
    psql -d nlretrieval_sales -f data/synthetic/seed_data.sql

Target row counts:
    suppliers          2,000
    customers         50,000
    products           5,000
    orders           500,000
    order_items      750,000
    invoices         400,000
    transactions   1,000,000
    returns           50,000
    daily_metrics      1,095  (3 years of daily data)
    cohort_metrics       500
    product_analytics  5,000
    stock_levels       5,000
    reorder_history    5,000
"""

import random
import math
import os
from datetime import date, datetime, timedelta

random.seed(42)

OUT_FILE = os.path.join(os.path.dirname(__file__), "seed_data.sql")
BATCH    = 500   # rows per INSERT batch

# ── Lookup data ───────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda",
    "William","Barbara","David","Elizabeth","Richard","Susan","Joseph","Jessica",
    "Thomas","Sarah","Charles","Karen","Christopher","Lisa","Daniel","Nancy",
    "Matthew","Betty","Anthony","Margaret","Mark","Sandra","Donald","Ashley",
    "Steven","Dorothy","Paul","Kimberly","Andrew","Emily","Joshua","Donna",
    "Kenneth","Michelle","Kevin","Carol","Brian","Amanda","George","Melissa",
    "Timothy","Deborah","Ronald","Stephanie","Edward","Rebecca","Jason","Sharon",
    "Jeffrey","Laura","Ryan","Cynthia","Jacob","Kathleen","Gary","Amy",
    "Nicholas","Angela","Eric","Shirley","Jonathan","Anna","Stephen","Brenda",
    "Larry","Pamela","Justin","Emma","Scott","Nicole","Brandon","Helen",
    "Benjamin","Samantha","Samuel","Katherine","Raymond","Christine","Gregory","Debra",
    "Frank","Rachel","Alexander","Carolyn","Patrick","Janet","Jack","Catherine",
    "Dennis","Maria","Jerry","Heather","Tyler","Diane","Aaron","Julie",
    "Jose","Joyce","Adam","Victoria","Henry","Kelly","Nathan","Christina",
    "Douglas","Lauren","Zachary","Joan","Peter","Evelyn","Kyle","Olivia",
]

LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas",
    "Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson","White",
    "Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker","Young",
    "Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores",
    "Green","Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell",
    "Carter","Roberts","Gomez","Phillips","Evans","Turner","Diaz","Parker",
    "Cruz","Edwards","Collins","Reyes","Stewart","Morris","Morales","Murphy",
    "Cook","Rogers","Gutierrez","Ortiz","Morgan","Cooper","Peterson","Bailey",
    "Reed","Kelly","Howard","Ramos","Kim","Cox","Ward","Richardson",
    "Watson","Brooks","Chavez","Wood","James","Bennett","Gray","Mendoza",
    "Ruiz","Hughes","Price","Alvarez","Castillo","Sanders","Patel","Myers",
    "Long","Ross","Foster","Jimenez","Powell","Jenkins","Perry","Russell",
]

PRODUCT_NAMES = [
    "Pro Wireless Headphones","4K Smart TV 65\"","Gaming Laptop 15\"","Bluetooth Speaker",
    "Mechanical Keyboard","Ergonomic Mouse","USB-C Hub 7-Port","Webcam 4K HD",
    "Portable SSD 1TB","External Hard Drive 2TB","Smart Watch Series 5","Fitness Tracker",
    "Noise Cancelling Earbuds","Tablet 10.5\"","E-Reader 6\"","Smart Home Hub",
    "WiFi Router Mesh","Security Camera Outdoor","Robot Vacuum Cleaner","Air Purifier HEPA",
    "Coffee Maker Programmable","Blender Pro 1200W","Instant Pot 8qt","Air Fryer XL",
    "Stand Mixer 5qt","Food Processor 14-Cup","Electric Kettle 1.7L","Toaster Oven Digital",
    "Running Shoes Pro","Yoga Mat Premium","Resistance Bands Set","Dumbbell Set Adjustable",
    "Foam Roller","Jump Rope Speed","Pull-Up Bar Doorway","Gym Gloves Pro",
    "Men's Dress Shirt","Women's Blazer","Casual Denim Jacket","Athletic T-Shirt",
    "Polo Shirt Classic","Compression Leggings","Running Shorts","Hoodie Pullover",
    "Winter Coat Insulated","Rain Jacket Waterproof","Formal Trousers","Casual Chinos",
    "Python Programming Book","Machine Learning Guide","Data Science Handbook","JavaScript Bible",
    "System Design Interview","Clean Code","Design Patterns","The Pragmatic Programmer",
    "Office Desk Adjustable","Ergonomic Chair Mesh","Monitor Stand Dual","Desk Organizer Set",
    "Filing Cabinet 3-Drawer","Bookshelf 5-Tier","Task Lamp LED","Whiteboard 4x3",
    "Vitamin D3 5000IU","Omega-3 Fish Oil","Whey Protein Powder","Multivitamin Daily",
    "Collagen Peptides","Probiotics 50B","Magnesium Glycinate","Melatonin 5mg",
    "LEGO Creator Expert","Board Game Settlers","Puzzle 1000pc","RC Car Off-Road",
    "Nerf Blaster Elite","Building Blocks 200pc","Dollhouse Deluxe","Science Kit Kids",
    "Moisturizer SPF 50","Retinol Serum","Vitamin C Serum","Hyaluronic Acid",
    "Foundation Matte","Mascara Waterproof","Lipstick Set 12","Eyeshadow Palette",
    "Shampoo Argan Oil","Conditioner Deep","Body Wash Luxury","Face Wash Gentle",
    "Chef Knife 8\"","Cutting Board Bamboo","Cast Iron Skillet","Non-Stick Pan Set",
    "Measuring Cups Set","Kitchen Scale Digital","Salad Spinner Large","Colander Stainless",
    "Backpack Travel 40L","Carry-On Luggage 20\"","Checked Luggage 28\"","Travel Pillow",
    "Packing Cubes Set","Passport Holder RFID","Luggage Tags Set","Travel Adapter Universal",
]

CATEGORIES = [
    "Electronics","Clothing","Home & Garden","Sports","Books",
    "Food & Beverages","Health & Beauty","Toys","Furniture",
]

REGIONS = ["North America","Europe","Asia Pacific","Latin America"]
REGION_WEIGHTS = [0.35, 0.30, 0.25, 0.10]

TIERS  = ["Bronze","Silver","Gold","Platinum","Enterprise"]
TIER_W = [0.50, 0.25, 0.15, 0.08, 0.02]

STATUSES = ["Pending","Processing","Shipped","Delivered","Cancelled"]
STATUS_W = [0.05, 0.10, 0.15, 0.60, 0.10]

COUNTRIES = ["USA","China","Germany","India","UK","Japan","Canada","Australia","Brazil","France"]

PAYMENT_METHODS  = ["Credit Card","Bank Transfer","PayPal","Check","Wire Transfer"]
PAYMENT_GATEWAYS = ["Stripe","PayPal","Square","Braintree","Adyen"]
INV_STATUSES     = ["Draft","Issued","Paid","Overdue","Cancelled"]
TXN_TYPES        = ["Sale","Return","Refund","Exchange"]
TXN_STATUSES     = ["Completed","Pending","Failed"]
RETURN_REASONS   = ["Defective","Wrong item","Changed mind","Better price","Damaged in shipping","Not as described"]
RETURN_STATUSES  = ["Pending","Approved","Completed","Rejected"]

START_DATE = date(2022, 1, 1)
END_DATE   = date(2025, 12, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days


# ── Helpers ───────────────────────────────────────────────────────────────────

def rand_date(start=START_DATE, end=END_DATE) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def rand_dt(start=START_DATE, end=END_DATE) -> datetime:
    d = rand_date(start, end)
    return datetime(d.year, d.month, d.day,
                    random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))


def seasonal_date() -> datetime:
    """Return date biased toward Q4 (Oct-Dec) and away from Jan-Feb."""
    while True:
        dt = rand_dt()
        m = dt.month
        # Q4 gets 40% extra weight, Jan-Feb get half weight
        if m in (10, 11, 12):
            if random.random() < 0.70:
                return dt
        elif m in (1, 2):
            if random.random() < 0.35:
                return dt
        else:
            if random.random() < 0.55:
                return dt


def lognormal_amount(mean=400.0, lo=10.0, hi=15000.0) -> float:
    """Lognormal order amount with realistic range."""
    mu    = math.log(mean)
    sigma = 0.8
    val   = math.exp(random.gauss(mu, sigma))
    return round(max(lo, min(hi, val)), 2)


def weighted_choice(choices, weights):
    r = random.random()
    cumulative = 0.0
    for c, w in zip(choices, weights):
        cumulative += w
        if r < cumulative:
            return c
    return choices[-1]


def sql_str(s) -> str:
    """Escape and quote a string value for SQL."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def sql_dt(dt) -> str:
    if dt is None:
        return "NULL"
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return f"'{dt}'"
    return f"'{dt.strftime('%Y-%m-%d %H:%M:%S')}'"


def sql_bool(b) -> str:
    return "TRUE" if b else "FALSE"


# ── DDL ───────────────────────────────────────────────────────────────────────

DDL = """
-- =============================================================================
-- NL Retrieval System — PostgreSQL Seed Data  (~2 M rows)
-- Generated by data/synthetic/generate_seed.py
-- Load: psql -d nlretrieval_sales -f seed_data.sql
-- =============================================================================

SET client_min_messages TO WARNING;

-- Drop tables (clean re-run)
DROP TABLE IF EXISTS reorder_history    CASCADE;
DROP TABLE IF EXISTS stock_levels       CASCADE;
DROP TABLE IF EXISTS product_analytics  CASCADE;
DROP TABLE IF EXISTS cohort_metrics     CASCADE;
DROP TABLE IF EXISTS daily_metrics      CASCADE;
DROP TABLE IF EXISTS returns            CASCADE;
DROP TABLE IF EXISTS transactions       CASCADE;
DROP TABLE IF EXISTS invoices           CASCADE;
DROP TABLE IF EXISTS order_items        CASCADE;
DROP TABLE IF EXISTS orders             CASCADE;
DROP TABLE IF EXISTS products           CASCADE;
DROP TABLE IF EXISTS customers          CASCADE;
DROP TABLE IF EXISTS suppliers          CASCADE;

-- suppliers
CREATE TABLE suppliers (
    supplier_id     VARCHAR(50)  PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    country         VARCHAR(100),
    category        VARCHAR(100),
    contact_email   VARCHAR(255),
    lead_time_days  INTEGER,
    rating          NUMERIC(3,2),
    is_active       BOOLEAN
);

-- customers
CREATE TABLE customers (
    customer_id   VARCHAR(50)  PRIMARY KEY,
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(255),
    region        VARCHAR(100),
    department    VARCHAR(100),
    created_date  TIMESTAMP,
    total_spent   NUMERIC(14,2),
    order_count   INTEGER,
    last_order_date TIMESTAMP,
    customer_tier VARCHAR(50)
);

-- products
CREATE TABLE products (
    product_id     VARCHAR(50)  PRIMARY KEY,
    name           VARCHAR(255) NOT NULL,
    category       VARCHAR(100),
    price          NUMERIC(12,2),
    cost           NUMERIC(12,2),
    description    TEXT,
    stock_quantity INTEGER,
    reorder_level  INTEGER,
    supplier_id    VARCHAR(50),
    created_date   TIMESTAMP,
    is_active      BOOLEAN,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

-- orders
CREATE TABLE orders (
    order_id         VARCHAR(50)  PRIMARY KEY,
    customer_id      VARCHAR(50)  NOT NULL,
    order_date       TIMESTAMP    NOT NULL,
    total_amount     NUMERIC(14,2),
    item_count       INTEGER,
    status           VARCHAR(50),
    shipping_address TEXT,
    shipping_cost    NUMERIC(10,2),
    tax_amount       NUMERIC(10,2),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- order_items
CREATE TABLE order_items (
    order_item_id VARCHAR(50)   PRIMARY KEY,
    order_id      VARCHAR(50)   NOT NULL,
    product_id    VARCHAR(50)   NOT NULL,
    quantity      INTEGER,
    unit_price    NUMERIC(12,2),
    discount_pct  NUMERIC(5,4),
    line_total    NUMERIC(14,2),
    FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- invoices
CREATE TABLE invoices (
    invoice_id     VARCHAR(50)  PRIMARY KEY,
    order_id       VARCHAR(50)  NOT NULL,
    customer_id    VARCHAR(50)  NOT NULL,
    invoice_date   TIMESTAMP,
    due_date       TIMESTAMP,
    subtotal       NUMERIC(14,2),
    tax_amount     NUMERIC(10,2),
    total_amount   NUMERIC(14,2),
    status         VARCHAR(50),
    payment_method VARCHAR(100),
    notes          TEXT,
    FOREIGN KEY (order_id)    REFERENCES orders(order_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- transactions
CREATE TABLE transactions (
    transaction_id   VARCHAR(50) PRIMARY KEY,
    order_id         VARCHAR(50) NOT NULL,
    customer_id      VARCHAR(50) NOT NULL,
    transaction_date TIMESTAMP,
    transaction_type VARCHAR(50),
    amount           NUMERIC(14,2),
    status           VARCHAR(50),
    payment_gateway  VARCHAR(100),
    metadata         JSONB,
    FOREIGN KEY (order_id)    REFERENCES orders(order_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- returns
CREATE TABLE returns (
    return_id   VARCHAR(50) PRIMARY KEY,
    order_id    VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    product_id  VARCHAR(50) NOT NULL,
    return_date TIMESTAMP,
    reason      VARCHAR(255),
    amount      NUMERIC(14,2),
    status      VARCHAR(50),
    FOREIGN KEY (order_id)    REFERENCES orders(order_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id)  REFERENCES products(product_id)
);

-- daily_metrics
CREATE TABLE daily_metrics (
    date                 DATE PRIMARY KEY,
    total_orders         INTEGER,
    total_revenue        NUMERIC(14,2),
    total_customers      INTEGER,
    avg_order_value      NUMERIC(12,2),
    new_customers        INTEGER,
    returning_customers  INTEGER,
    conversion_rate      NUMERIC(8,6)
);

-- cohort_metrics
CREATE TABLE cohort_metrics (
    cohort_id        VARCHAR(50) PRIMARY KEY,
    cohort_date      DATE,
    cohort_size      INTEGER,
    retention_week_1 NUMERIC(6,4),
    retention_week_4 NUMERIC(6,4),
    retention_week_12 NUMERIC(6,4),
    avg_ltv          NUMERIC(12,2),
    churn_rate       NUMERIC(6,4)
);

-- product_analytics
CREATE TABLE product_analytics (
    product_id           VARCHAR(50) PRIMARY KEY,
    total_units_sold     INTEGER,
    total_revenue        NUMERIC(14,2),
    avg_rating           NUMERIC(4,2),
    review_count         INTEGER,
    return_rate          NUMERIC(6,4),
    views                INTEGER,
    page_conversion_rate NUMERIC(6,4)
);

-- stock_levels
CREATE TABLE stock_levels (
    product_id          VARCHAR(50) PRIMARY KEY,
    warehouse           VARCHAR(100),
    quantity_on_hand    INTEGER,
    quantity_reserved   INTEGER,
    quantity_available  INTEGER,
    last_count_date     TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- reorder_history
CREATE TABLE reorder_history (
    reorder_id             VARCHAR(50) PRIMARY KEY,
    product_id             VARCHAR(50) NOT NULL,
    reorder_date           TIMESTAMP,
    quantity_ordered       INTEGER,
    supplier_id            VARCHAR(50),
    expected_delivery_date TIMESTAMP,
    actual_delivery_date   TIMESTAMP,
    cost_per_unit          NUMERIC(12,2),
    total_cost             NUMERIC(14,2),
    FOREIGN KEY (product_id)  REFERENCES products(product_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);
"""

INDEXES = """
-- Indexes for common query patterns
CREATE INDEX idx_orders_customer_id  ON orders(customer_id);
CREATE INDEX idx_orders_date         ON orders(order_date);
CREATE INDEX idx_orders_status       ON orders(status);
CREATE INDEX idx_orders_amount       ON orders(total_amount);
CREATE INDEX idx_order_items_order   ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_invoices_order      ON invoices(order_id);
CREATE INDEX idx_invoices_customer   ON invoices(customer_id);
CREATE INDEX idx_transactions_order  ON transactions(order_id);
CREATE INDEX idx_transactions_date   ON transactions(transaction_date);
CREATE INDEX idx_returns_order       ON returns(order_id);
CREATE INDEX idx_returns_customer    ON returns(customer_id);
CREATE INDEX idx_products_category   ON products(category);
CREATE INDEX idx_products_supplier   ON products(supplier_id);
CREATE INDEX idx_customers_region    ON customers(region);
CREATE INDEX idx_customers_tier      ON customers(customer_tier);
CREATE INDEX idx_daily_metrics_date  ON daily_metrics(date);
"""


# ── Row generators ─────────────────────────────────────────────────────────────

def gen_suppliers(n=2000):
    rows = []
    for i in range(1, n + 1):
        rows.append((
            f"SUP_{i:04d}",
            f"{random.choice(LAST_NAMES)} & {random.choice(LAST_NAMES)} Supply Co",
            random.choice(COUNTRIES),
            random.choice(CATEGORIES),
            f"contact@supplier{i}.com",
            random.randint(3, 90),
            round(random.uniform(2.5, 5.0), 2),
            random.random() > 0.08,
        ))
    return rows


def gen_customers(n=50000):
    rows = []
    depts = ["Sales","Marketing","Operations","Finance","IT","Legal","HR","Engineering"]
    for i in range(1, n + 1):
        fn  = random.choice(FIRST_NAMES)
        ln  = random.choice(LAST_NAMES)
        reg = weighted_choice(REGIONS, REGION_WEIGHTS)
        tier = weighted_choice(TIERS, TIER_W)
        created = rand_dt(START_DATE, date(2025, 6, 30))
        last_ord = created + timedelta(days=random.randint(1, 400))
        if last_ord > datetime(2025, 12, 31):
            last_ord = datetime(2025, 12, 31)
        rows.append((
            f"CUST_{i:07d}",
            f"{fn} {ln}",
            f"{fn.lower()}.{ln.lower()}{i}@email.com",
            reg,
            random.choice(depts),
            created,
            round(random.uniform(50, 80000), 2),
            random.randint(1, 200),
            last_ord,
            tier,
        ))
    return rows


def gen_products(n=5000, n_sup=2000):
    rows = []
    base_names = PRODUCT_NAMES
    for i in range(1, n + 1):
        base = random.choice(base_names)
        cat  = random.choice(CATEGORIES)
        price = round(random.uniform(5, 2000), 2)
        cost  = round(price * random.uniform(0.25, 0.65), 2)
        rows.append((
            f"PROD_{i:06d}",
            f"{base} #{i}",
            cat,
            price,
            cost,
            f"High-quality {base.lower()} — SKU {i:06d}",
            random.randint(0, 50000),
            random.randint(50, 2000),
            f"SUP_{random.randint(1, n_sup):04d}",
            rand_dt(START_DATE, date(2024, 12, 31)),
            random.random() > 0.05,
        ))
    return rows


def gen_orders(n=500000, n_cust=50000):
    rows = []
    for i in range(1, n + 1):
        cust_id = f"CUST_{random.randint(1, n_cust):07d}"
        odt     = seasonal_date()
        amount  = lognormal_amount()
        items   = random.randint(1, 8)
        status  = weighted_choice(STATUSES, STATUS_W)
        region  = weighted_choice(REGIONS, REGION_WEIGHTS)
        ship    = round(random.uniform(0, 75), 2)
        tax     = round(amount * random.uniform(0.05, 0.12), 2)
        rows.append((
            f"ORD_{i:08d}",
            cust_id,
            odt,
            amount,
            items,
            status,
            f"{region}, Street {random.randint(1,999)}",
            ship,
            tax,
        ))
    return rows


def gen_order_items(n=750000, n_orders=500000, n_prod=5000):
    rows = []
    for i in range(1, n + 1):
        oid  = f"ORD_{random.randint(1, n_orders):08d}"
        pid  = f"PROD_{random.randint(1, n_prod):06d}"
        qty  = random.randint(1, 15)
        up   = round(random.uniform(5, 2000), 2)
        disc = round(random.uniform(0, 0.30), 4)
        lt   = round(up * qty * (1 - disc), 2)
        rows.append((
            f"OI_{i:09d}",
            oid,
            pid,
            qty,
            up,
            disc,
            lt,
        ))
    return rows


def gen_invoices(n=400000, n_orders=500000, n_cust=50000):
    rows = []
    for i in range(1, n + 1):
        oid    = f"ORD_{random.randint(1, n_orders):08d}"
        cid    = f"CUST_{random.randint(1, n_cust):07d}"
        idate  = rand_dt()
        due    = idate + timedelta(days=30)
        sub    = round(random.uniform(10, 14000), 2)
        tax    = round(sub * random.uniform(0.05, 0.12), 2)
        total  = round(sub + tax, 2)
        rows.append((
            f"INV_{i:08d}",
            oid,
            cid,
            idate,
            due,
            sub,
            tax,
            total,
            random.choice(INV_STATUSES),
            random.choice(PAYMENT_METHODS),
            "Invoice generated automatically",
        ))
    return rows


def gen_transactions(n=1000000, n_orders=500000, n_cust=50000):
    rows = []
    for i in range(1, n + 1):
        oid   = f"ORD_{random.randint(1, n_orders):08d}"
        cid   = f"CUST_{random.randint(1, n_cust):07d}"
        tdate = rand_dt()
        amt   = round(random.uniform(5, 15000), 2)
        rows.append((
            f"TXN_{i:010d}",
            oid,
            cid,
            tdate,
            random.choice(TXN_TYPES),
            amt,
            random.choice(TXN_STATUSES),
            random.choice(PAYMENT_GATEWAYS),
            '{"ip": "10.' + str(random.randint(0,255)) + '.' + str(random.randint(0,255)) + '.' + str(random.randint(1,254)) + '"}',
        ))
    return rows


def gen_returns(n=50000, n_orders=500000, n_cust=50000, n_prod=5000):
    rows = []
    for i in range(1, n + 1):
        oid  = f"ORD_{random.randint(1, n_orders):08d}"
        cid  = f"CUST_{random.randint(1, n_cust):07d}"
        pid  = f"PROD_{random.randint(1, n_prod):06d}"
        rdate = rand_dt()
        rows.append((
            f"RET_{i:07d}",
            oid,
            cid,
            pid,
            rdate,
            random.choice(RETURN_REASONS),
            round(random.uniform(5, 5000), 2),
            random.choice(RETURN_STATUSES),
        ))
    return rows


def gen_daily_metrics(days=1095):
    rows = []
    base_rev = 180000
    base_ord = 400
    for day in range(days):
        d = START_DATE + timedelta(days=day)
        # Seasonal factor: Q4 +40%, Jan-Feb -30%
        m = d.month
        sf = 1.40 if m in (10,11,12) else (0.70 if m in (1,2) else 1.0)
        rev = round(base_rev * sf * random.uniform(0.7, 1.4), 2)
        ord_cnt = int(base_ord * sf * random.uniform(0.7, 1.4))
        rows.append((
            d,
            ord_cnt,
            rev,
            int(ord_cnt * random.uniform(0.5, 0.9)),
            round(rev / max(ord_cnt, 1), 2),
            int(ord_cnt * random.uniform(0.05, 0.20)),
            int(ord_cnt * random.uniform(0.30, 0.80)),
            round(random.uniform(0.01, 0.12), 6),
        ))
    return rows


def gen_cohort_metrics(n=500):
    rows = []
    for i in range(1, n + 1):
        cd = rand_date()
        rows.append((
            f"COHORT_{i:04d}",
            cd,
            random.randint(100, 10000),
            round(random.uniform(0.50, 0.95), 4),
            round(random.uniform(0.20, 0.80), 4),
            round(random.uniform(0.10, 0.60), 4),
            round(random.uniform(200, 10000), 2),
            round(random.uniform(0.01, 0.25), 4),
        ))
    return rows


def gen_product_analytics(n=5000):
    rows = []
    for i in range(1, n + 1):
        rows.append((
            f"PROD_{i:06d}",
            random.randint(0, 100000),
            round(random.uniform(0, 2000000), 2),
            round(random.uniform(1.0, 5.0), 2),
            random.randint(0, 5000),
            round(random.uniform(0, 0.25), 4),
            random.randint(0, 500000),
            round(random.uniform(0, 0.15), 4),
        ))
    return rows


def gen_stock_levels(n_prod=5000):
    rows = []
    warehouses = ["Warehouse A","Warehouse B","Warehouse C","Distribution Center East","Distribution Center West"]
    for i in range(1, n_prod + 1):
        pid = f"PROD_{i:06d}"
        qoh = random.randint(0, 100000)
        qr  = random.randint(0, min(qoh, 5000))
        rows.append((
            pid,
            random.choice(warehouses),
            qoh,
            qr,
            qoh - qr,
            rand_dt(date(2024, 1, 1), date(2025, 12, 31)),
        ))
    return rows


def gen_reorder_history(n=5000, n_prod=5000, n_sup=2000):
    rows = []
    for i in range(1, n + 1):
        pid  = f"PROD_{random.randint(1, n_prod):06d}"
        sid  = f"SUP_{random.randint(1, n_sup):04d}"
        rdt  = rand_dt()
        exp  = rdt + timedelta(days=random.randint(5, 60))
        act  = rdt + timedelta(days=random.randint(5, 65))
        cpu  = round(random.uniform(1, 800), 2)
        qty  = random.randint(50, 10000)
        rows.append((
            f"RO_{i:07d}",
            pid,
            rdt,
            qty,
            sid,
            exp,
            act,
            cpu,
            round(cpu * qty, 2),
        ))
    return rows


# ── Writer ────────────────────────────────────────────────────────────────────

def write_inserts(f, table: str, cols: list, rows: list):
    """Write batched INSERT statements (BATCH rows per statement)."""
    if not rows:
        return

    col_str = ", ".join(cols)

    for start in range(0, len(rows), BATCH):
        chunk = rows[start:start + BATCH]
        values_parts = []
        for row in chunk:
            parts = []
            for v in row:
                if v is None:
                    parts.append("NULL")
                elif isinstance(v, bool):
                    parts.append(sql_bool(v))
                elif isinstance(v, (int, float)):
                    parts.append(str(v))
                elif isinstance(v, (datetime, date)):
                    parts.append(sql_dt(v))
                else:
                    parts.append(sql_str(v))
            values_parts.append("(" + ", ".join(parts) + ")")

        f.write(f"INSERT INTO {table} ({col_str}) VALUES\n")
        f.write(",\n".join(values_parts))
        f.write(";\n")

    f.write(f"-- {table}: {len(rows):,} rows loaded\n\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Generating seed data → {OUT_FILE}")
    print("This may take a few minutes for ~2M rows...")

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(DDL)
        f.write("\n-- ── DATA ──────────────────────────────────────────────────────────\n\n")

        steps = [
            ("suppliers",         ["supplier_id","name","country","category","contact_email","lead_time_days","rating","is_active"],
             gen_suppliers, {"n": 2000}),
            ("customers",         ["customer_id","name","email","region","department","created_date","total_spent","order_count","last_order_date","customer_tier"],
             gen_customers, {"n": 50000}),
            ("products",          ["product_id","name","category","price","cost","description","stock_quantity","reorder_level","supplier_id","created_date","is_active"],
             gen_products, {"n": 5000, "n_sup": 2000}),
            ("orders",            ["order_id","customer_id","order_date","total_amount","item_count","status","shipping_address","shipping_cost","tax_amount"],
             gen_orders, {"n": 500000, "n_cust": 50000}),
            ("order_items",       ["order_item_id","order_id","product_id","quantity","unit_price","discount_pct","line_total"],
             gen_order_items, {"n": 750000, "n_orders": 500000, "n_prod": 5000}),
            ("invoices",          ["invoice_id","order_id","customer_id","invoice_date","due_date","subtotal","tax_amount","total_amount","status","payment_method","notes"],
             gen_invoices, {"n": 400000, "n_orders": 500000, "n_cust": 50000}),
            ("transactions",      ["transaction_id","order_id","customer_id","transaction_date","transaction_type","amount","status","payment_gateway","metadata"],
             gen_transactions, {"n": 1000000, "n_orders": 500000, "n_cust": 50000}),
            ("returns",           ["return_id","order_id","customer_id","product_id","return_date","reason","amount","status"],
             gen_returns, {"n": 50000, "n_orders": 500000, "n_cust": 50000, "n_prod": 5000}),
            ("daily_metrics",     ["date","total_orders","total_revenue","total_customers","avg_order_value","new_customers","returning_customers","conversion_rate"],
             gen_daily_metrics, {"days": 1095}),
            ("cohort_metrics",    ["cohort_id","cohort_date","cohort_size","retention_week_1","retention_week_4","retention_week_12","avg_ltv","churn_rate"],
             gen_cohort_metrics, {"n": 500}),
            ("product_analytics", ["product_id","total_units_sold","total_revenue","avg_rating","review_count","return_rate","views","page_conversion_rate"],
             gen_product_analytics, {"n": 5000}),
            ("stock_levels",      ["product_id","warehouse","quantity_on_hand","quantity_reserved","quantity_available","last_count_date"],
             gen_stock_levels, {"n_prod": 5000}),
            ("reorder_history",   ["reorder_id","product_id","reorder_date","quantity_ordered","supplier_id","expected_delivery_date","actual_delivery_date","cost_per_unit","total_cost"],
             gen_reorder_history, {"n": 5000, "n_prod": 5000, "n_sup": 2000}),
        ]

        total_rows = 0
        for table, cols, gen_fn, kwargs in steps:
            print(f"  Generating {table}...", end=" ", flush=True)
            f.write(f"BEGIN;\n")
            rows = gen_fn(**kwargs)
            write_inserts(f, table, cols, rows)
            f.write("COMMIT;\n\n")
            total_rows += len(rows)
            print(f"{len(rows):,} rows")

        f.write(INDEXES)
        f.write("\n-- VACUUM ANALYZE for query planner statistics\n")
        f.write("VACUUM ANALYZE;\n")
        f.write(f"\n-- Total rows: {total_rows:,}\n")
        f.write("-- Seed data load complete.\n")

    size_mb = os.path.getsize(OUT_FILE) / (1024 * 1024)
    print(f"\nDone!  {OUT_FILE}")
    print(f"  Total rows : {total_rows:,}")
    print(f"  File size  : {size_mb:.1f} MB")
    print("\nTo load into PostgreSQL:")
    print("  createdb nlretrieval_sales")
    print("  psql -d nlretrieval_sales -f data/synthetic/seed_data.sql")


if __name__ == "__main__":
    main()
