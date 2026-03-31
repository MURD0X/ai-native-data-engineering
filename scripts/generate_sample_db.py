"""
Generate sample orders.sqlite for before/ and after/ pipeline examples.

Usage:
    python scripts/generate_sample_db.py
"""

import sqlite3
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

CUSTOMERS = [
    ("C001", "Alice Mercer",    "14 Oak Lane, Portland OR 97201",  "alice@example.com"),
    ("C002", "Bob Hartmann",    "292 Pine St, Seattle WA 98101",    "bob@example.com"),
    ("C003", "Carol Nguyen",    "7 Elm Ave, Denver CO 80201",       "carol@example.com"),
    ("C004", "David Osei",      "88 Maple Rd, Austin TX 78701",     "david@example.com"),
    ("C005", "Elena Vasquez",   "3 Birch Blvd, Chicago IL 60601",   "elena@example.com"),
]

PRODUCTS = [
    ("P001", "Wireless Headphones",  "in_stock",    120),
    ("P002", "Mechanical Keyboard",  "in_stock",    250),
    ("P003", "USB-C Hub",            "low_stock",    45),
    ("P004", "Monitor Stand",        "out_of_stock", 80),
    ("P005", "Desk Lamp",            "in_stock",     35),
    ("P006", "Webcam HD",            "in_stock",     90),
    ("P007", "Laptop Stand",         "in_stock",    110),
    ("P008", "Mouse Pad XL",         "in_stock",     25),
]

PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "bank_transfer"]

def generate_orders(n_days=45, seed=42):
    random.seed(seed)
    orders = []
    order_id = 1001
    base_date = datetime(2024, 1, 1)

    for day_offset in range(n_days):
        order_date = base_date + timedelta(days=day_offset)
        # 3-8 orders per day
        n_orders = random.randint(3, 8)
        for _ in range(n_orders):
            customer = random.choice(CUSTOMERS)
            product = random.choice(PRODUCTS)
            # C001 (Alice) is a high-value VIP customer
            base_amount = product[3]
            if customer[0] == "C001":
                base_amount *= random.uniform(1.5, 3.5)
            else:
                base_amount *= random.uniform(0.8, 1.4)

            hour = random.randint(8, 20)
            minute = random.randint(0, 59)
            ts = order_date.replace(hour=hour, minute=minute)

            orders.append((
                order_id,
                customer[0],
                product[0],
                round(base_amount, 2),
                ts.strftime("%Y-%m-%d %H:%M:%S"),
                random.choice(PAYMENT_METHODS),
            ))
            order_id += 1

    return orders


def create_db(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    conn = sqlite3.connect(path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            address TEXT,
            email TEXT
        )
    """)
    cur.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?)",
        CUSTOMERS,
    )

    cur.execute("""
        CREATE TABLE inventory (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            stock_status TEXT NOT NULL,
            unit_price REAL NOT NULL
        )
    """)
    cur.executemany(
        "INSERT INTO inventory VALUES (?, ?, ?, ?)",
        PRODUCTS,
    )

    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            amount REAL NOT NULL,
            timestamp TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (product_id) REFERENCES inventory(product_id)
        )
    """)
    cur.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
        generate_orders(),
    )

    conn.commit()
    conn.close()
    print(f"Created {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    root = Path(__file__).parent.parent / "patterns" / "bootstrap-standards"
    before_db = root / "before" / "orders.sqlite"
    after_db  = root / "after"  / "orders.sqlite"

    create_db(before_db)
    shutil.copy(before_db, after_db)
    print(f"Copied to {after_db}")
    print("Done.")
