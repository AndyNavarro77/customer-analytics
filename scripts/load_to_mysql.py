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
CSV_PATH = "data/online_retail_II.csv"
# ────────────────────────────────────────────────────────

def load_data(path):
    print("Cargando CSV...")
    df = pd.read_csv(path, encoding="utf-8")
    print(f"  Filas raw: {len(df):,}")
    return df

def clean_data(df):
    print("Limpiando datos...")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Renombrar columnas clave si vienen con nombres originales de Kaggle
    rename_map = {
        "invoice":     "invoice",
        "stockcode":   "stock_code",
        "description": "description",
        "quantity":    "quantity",
        "invoicedate": "invoice_date",
        "price":       "price",
        "customer id": "customer_id",
        "customerid":  "customer_id",
        "country":     "country",
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    # Tipos
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["customer_id"]  = pd.to_numeric(df["customer_id"], errors="coerce")

    # Filtros de calidad
    df = df[df["quantity"] > 0]
    df = df[df["price"] > 0]
    df = df.dropna(subset=["customer_id"])
    df["customer_id"] = df["customer_id"].astype(int)

    # Columna de revenue
    df["revenue"] = df["quantity"] * df["price"]

    print(f"  Filas limpias: {len(df):,}")
    return df

def create_db(engine):
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
        conn.commit()
    print(f"  Base de datos '{DB_NAME}' lista.")

def load_to_mysql(df, engine):
    print("Cargando a MySQL...")
    t0 = time.time()
    df.to_sql(
        name="transactions",
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=5000,
        method="multi"
    )
    print(f"  Cargado en {time.time()-t0:.1f}s")

def create_indexes(engine):
    print("Creando índices...")
    queries = [
        "ALTER TABLE transactions ADD INDEX idx_customer (customer_id)",
        "ALTER TABLE transactions ADD INDEX idx_date (invoice_date)",
        "ALTER TABLE transactions ADD INDEX idx_country (country)",
        "ALTER TABLE transactions ADD INDEX idx_invoice (invoice(20))",
    ]
    with engine.connect() as conn:
        for q in queries:
            try:
                conn.execute(text(q))
                conn.commit()
            except Exception as e:
                print(f"  (índice ya existe o error menor: {e})")
    print("  Índices creados.")

def verify(engine):
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
        sample = conn.execute(text("SELECT MIN(invoice_date), MAX(invoice_date) FROM transactions")).fetchone()
        customers = conn.execute(text("SELECT COUNT(DISTINCT customer_id) FROM transactions")).scalar()
    print(f"\n✅ Verificación:")
    print(f"   Filas totales  : {total:,}")
    print(f"   Clientes únicos: {customers:,}")
    print(f"   Rango de fechas: {sample[0]} → {sample[1]}")

if __name__ == "__main__":
    # 1. Crear DB
    base_engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/")
    create_db(base_engine)

    # 2. Conectar a la DB
    engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    # 3. ETL
    df = load_data(CSV_PATH)
    df = clean_data(df)
    load_to_mysql(df, engine)
    create_indexes(engine)
    verify(engine)

    print("\n✅ Pipeline completo. Listo para conectar desde Power BI.")