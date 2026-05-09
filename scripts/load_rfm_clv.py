import pandas as pd
from sqlalchemy import create_engine, text
import time
from dotenv import load_dotenv
import os

# ── CONFIG ──────────────────────────────────────────────
load_dotenv()

DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_NAME     = os.getenv("DB_NAME")
# ────────────────────────────────────────────────────────

engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def load_rfm(engine):
    print("Cargando rfm_segments...")
    df = pd.read_csv("data/rfm_segments.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df.to_sql("rfm_segments", con=engine, if_exists="replace", index=False)
    print(f"  ✅ rfm_segments: {len(df):,} filas")

    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE rfm_segments ADD INDEX idx_rfm_customer (customer_id)"))
        conn.execute(text("ALTER TABLE rfm_segments ADD INDEX idx_segment (segment(50))"))
        conn.commit()
    print("  Índices creados.")

def load_clv(engine):
    print("Cargando clv_customers...")
    df = pd.read_csv("data/clv_customers.csv")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df.to_sql("clv_customers", con=engine, if_exists="replace", index=False)
    print(f"  ✅ clv_customers: {len(df):,} filas")

    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE clv_customers ADD INDEX idx_clv_customer (customer_id)"))
        conn.execute(text("ALTER TABLE clv_customers ADD INDEX idx_clv_segment (segment(50))"))
        conn.commit()
    print("  Índices creados.")

def verify(engine):
    with engine.connect() as conn:
        segs = conn.execute(text("""
            SELECT segment, COUNT(*) as customers, 
                   ROUND(AVG(monetary), 2) as avg_monetary
            FROM rfm_segments 
            GROUP BY segment 
            ORDER BY avg_monetary DESC
        """)).fetchall()

        print("\n✅ Segmentos en MySQL:")
        print(f"{'Segment':<22} {'Customers':>10} {'Avg Monetary':>14}")
        print("-" * 48)
        for row in segs:
            print(f"{row[0]:<22} {row[1]:>10,} {row[2]:>14,.2f}")

        total_clv = conn.execute(text(
            "SELECT ROUND(AVG(clv_12months), 2) FROM clv_customers"
        )).scalar()
        print(f"\n  Avg CLV (12m): ${total_clv:,.2f}")

if __name__ == "__main__":
    load_rfm(engine)
    load_clv(engine)
    verify(engine)
    print("\n✅ Tablas analíticas listas en MySQL.")