import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = 'orders.sqlite'


def load_orders():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM orders", conn)
    conn.close()
    return df


def enrich_customer_data(orders_df):
    conn = sqlite3.connect(DB_PATH)
    customers = pd.read_sql("SELECT * FROM customers", conn)
    conn.close()
    return orders_df.merge(customers, on='customer_id')


def calculate_metrics(df):
    df = df.copy()
    df['order_date'] = pd.to_datetime(df['timestamp']).dt.date
    df = df.sort_values('timestamp')
    df['rolling_30d_revenue'] = (
        df.groupby('customer_id')['amount']
        .transform(lambda x: x.rolling(30, min_periods=1).sum())
    )
    return df


def join_inventory(df):
    conn = sqlite3.connect(DB_PATH)
    inventory = pd.read_sql("SELECT * FROM inventory", conn)
    conn.close()
    return df.merge(inventory, on='product_id', how='left')


def aggregate_daily_summary(df):
    summary = df.groupby(['order_date', 'customer_id']).agg(
        daily_revenue=('amount', 'sum'),
        rolling_30d_revenue=('rolling_30d_revenue', 'last'),
        stock_status=('stock_status', 'first'),
        customer_name=('customer_name', 'first'),
        address=('address', 'first'),
    ).reset_index()
    summary = summary.rename(columns={'order_date': 'date'})
    return summary


if __name__ == "__main__":
    orders = load_orders()
    enriched = enrich_customer_data(orders)
    with_metrics = calculate_metrics(enriched)
    with_inventory = join_inventory(with_metrics)
    summary = aggregate_daily_summary(with_inventory)
    summary.to_csv('daily_summary.csv', index=False)
    print("Done")
