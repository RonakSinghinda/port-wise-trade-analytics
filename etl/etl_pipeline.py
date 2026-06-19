#!/usr/bin/env python3
"""
Port-Wise Trade Analytics — ETL Pipeline
=========================================
Generates realistic sample trade data for 10 major Indian ports
and loads it into a SQLite database.

Run:
    python etl/etl_pipeline.py

Output:
    data/trade_analytics.db  (SQLite database, ~5000+ trade records)
"""

import sqlite3
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "trade_analytics.db"

# ─────────────────────────────────────────────────────────────────────────────
# Seed for reproducibility
# ─────────────────────────────────────────────────────────────────────────────
np.random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# Master Data
# ─────────────────────────────────────────────────────────────────────────────

PORTS = [
    {"id": 1,  "name": "Jawaharlal Nehru Port (JNPT)", "code": "INJNP", "city": "Navi Mumbai",   "state": "Maharashtra",    "lat": 18.9388, "lon": 72.9561, "port_type": "Major Port Trust"},
    {"id": 2,  "name": "Deendayal Port (Kandla)",       "code": "INKND", "city": "Gandhidham",    "state": "Gujarat",        "lat": 23.0316, "lon": 70.2177, "port_type": "Major Port Trust"},
    {"id": 3,  "name": "Mundra Port",                   "code": "INMUN", "city": "Mundra",         "state": "Gujarat",        "lat": 22.8374, "lon": 69.7227, "port_type": "Private Port"},
    {"id": 4,  "name": "Chennai Port",                  "code": "INMAA", "city": "Chennai",        "state": "Tamil Nadu",     "lat": 13.0827, "lon": 80.2707, "port_type": "Major Port Trust"},
    {"id": 5,  "name": "Visakhapatnam Port",            "code": "INVTZ", "city": "Visakhapatnam", "state": "Andhra Pradesh", "lat": 17.6868, "lon": 83.2185, "port_type": "Major Port Trust"},
    {"id": 6,  "name": "Paradip Port",                  "code": "INPRD", "city": "Paradip",        "state": "Odisha",         "lat": 20.3152, "lon": 86.6110, "port_type": "Major Port Trust"},
    {"id": 7,  "name": "Kolkata Port",                  "code": "INCCU", "city": "Kolkata",        "state": "West Bengal",    "lat": 22.5726, "lon": 88.3639, "port_type": "Major Port Trust"},
    {"id": 8,  "name": "Kochi Port",                    "code": "INCOK", "city": "Kochi",          "state": "Kerala",         "lat": 9.9312,  "lon": 76.2673, "port_type": "Major Port Trust"},
    {"id": 9,  "name": "New Mangalore Port",            "code": "INMRM", "city": "Mangalore",      "state": "Karnataka",      "lat": 12.9141, "lon": 74.8560, "port_type": "Major Port Trust"},
    {"id": 10, "name": "Kamarajar Port (Ennore)",       "code": "INENN", "city": "Ennore",          "state": "Tamil Nadu",     "lat": 13.2143, "lon": 80.3275, "port_type": "Major Port Authority"},
]

COMMODITIES = [
    {"id": 1,  "name": "Crude Oil",             "category": "Energy"},
    {"id": 2,  "name": "Coal",                  "category": "Energy"},
    {"id": 3,  "name": "Containers",            "category": "General Cargo"},
    {"id": 4,  "name": "Iron Ore",              "category": "Minerals"},
    {"id": 5,  "name": "Fertilizers",           "category": "Chemicals"},
    {"id": 6,  "name": "POL Products",          "category": "Energy"},
    {"id": 7,  "name": "LNG / LPG",             "category": "Energy"},
    {"id": 8,  "name": "Food Grains",           "category": "Agriculture"},
    {"id": 9,  "name": "Chemicals & Pharma",    "category": "Chemicals"},
    {"id": 10, "name": "Steel Products",        "category": "Metals"},
    {"id": 11, "name": "Machinery & Equipment", "category": "Industrial"},
    {"id": 12, "name": "Textiles & Apparel",    "category": "Consumer Goods"},
    {"id": 13, "name": "Minerals & Ores",       "category": "Minerals"},
    {"id": 14, "name": "Timber & Wood",         "category": "Agriculture"},
    {"id": 15, "name": "General Cargo",         "category": "General Cargo"},
]

COUNTRIES = [
    {"id": 1,  "name": "China",         "code": "CN", "region": "Asia Pacific"},
    {"id": 2,  "name": "United States", "code": "US", "region": "Americas"},
    {"id": 3,  "name": "UAE",           "code": "AE", "region": "Middle East"},
    {"id": 4,  "name": "Saudi Arabia",  "code": "SA", "region": "Middle East"},
    {"id": 5,  "name": "Australia",     "code": "AU", "region": "Asia Pacific"},
    {"id": 6,  "name": "Russia",        "code": "RU", "region": "Europe"},
    {"id": 7,  "name": "Indonesia",     "code": "ID", "region": "Asia Pacific"},
    {"id": 8,  "name": "South Korea",   "code": "KR", "region": "Asia Pacific"},
    {"id": 9,  "name": "Germany",       "code": "DE", "region": "Europe"},
    {"id": 10, "name": "Japan",         "code": "JP", "region": "Asia Pacific"},
    {"id": 11, "name": "Bangladesh",    "code": "BD", "region": "South Asia"},
    {"id": 12, "name": "Sri Lanka",     "code": "LK", "region": "South Asia"},
    {"id": 13, "name": "Singapore",     "code": "SG", "region": "Asia Pacific"},
    {"id": 14, "name": "Malaysia",      "code": "MY", "region": "Asia Pacific"},
    {"id": 15, "name": "Iraq",          "code": "IQ", "region": "Middle East"},
    {"id": 16, "name": "Iran",          "code": "IR", "region": "Middle East"},
    {"id": 17, "name": "Brazil",        "code": "BR", "region": "Americas"},
    {"id": 18, "name": "South Africa",  "code": "ZA", "region": "Africa"},
    {"id": 19, "name": "Canada",        "code": "CA", "region": "Americas"},
    {"id": 20, "name": "Netherlands",   "code": "NL", "region": "Europe"},
]

# ─────────────────────────────────────────────────────────────────────────────
# Affinity / Weight Matrices
# ─────────────────────────────────────────────────────────────────────────────

# (commodity_id, weight_fraction) per port — must sum to 1.0
PORT_COMMODITY_AFFINITY = {
    1:  [(3, 0.55), (15, 0.15), (10, 0.12), (9,  0.10), (12, 0.08)],    # JNPT
    2:  [(1, 0.35), (6,  0.20), (5,  0.18), (8,  0.12), (7,  0.08), (15, 0.07)],  # Kandla
    3:  [(3, 0.38), (2,  0.25), (1,  0.20), (5,  0.12), (15, 0.05)],    # Mundra
    4:  [(3, 0.40), (2,  0.20), (4,  0.15), (10, 0.15), (6,  0.10)],    # Chennai
    5:  [(4, 0.38), (5,  0.20), (2,  0.20), (6,  0.10), (3,  0.12)],    # Vizag
    6:  [(4, 0.30), (2,  0.30), (1,  0.25), (5,  0.15)],                 # Paradip
    7:  [(3, 0.35), (10, 0.25), (8,  0.20), (15, 0.20)],                 # Kolkata
    8:  [(3, 0.35), (1,  0.28), (7,  0.22), (15, 0.15)],                 # Kochi
    9:  [(1, 0.48), (2,  0.25), (6,  0.15), (15, 0.12)],                 # New Mangalore
    10: [(2, 0.45), (3,  0.25), (4,  0.20), (10, 0.10)],                 # Ennore
}

# Import vs Export tendency (import_weight, export_weight)
COMMODITY_TRADE_TENDENCY = {
    1:  (0.92, 0.08),   # Crude Oil        → mostly import
    2:  (0.88, 0.12),   # Coal             → mostly import
    3:  (0.50, 0.50),   # Containers       → balanced
    4:  (0.28, 0.72),   # Iron Ore         → mostly export
    5:  (0.78, 0.22),   # Fertilizers      → mostly import
    6:  (0.42, 0.58),   # POL Products     → export focus
    7:  (0.82, 0.18),   # LNG/LPG          → mostly import
    8:  (0.44, 0.56),   # Food Grains      → balanced
    9:  (0.33, 0.67),   # Chemicals        → export focus
    10: (0.40, 0.60),   # Steel            → balanced-export
    11: (0.72, 0.28),   # Machinery        → mostly import
    12: (0.18, 0.82),   # Textiles         → mostly export
    13: (0.42, 0.58),   # Minerals         → balanced
    14: (0.62, 0.38),   # Timber           → mostly import
    15: (0.50, 0.50),   # General Cargo    → balanced
}

# Primary trading countries per commodity (country_id list)
COMMODITY_COUNTRY_AFFINITY = {
    1:  [4, 15, 3, 16, 6],         # Crude Oil    → Middle East, Russia
    2:  [7, 5, 6, 17, 18],         # Coal         → Indonesia, Australia, Russia, Brazil, SA
    3:  [1, 13, 14, 8, 2],         # Containers   → China, Singapore, Malaysia, Korea, USA
    4:  [5, 17, 18, 3, 1],         # Iron Ore     → Australia, Brazil, SA
    5:  [6, 4, 17, 19, 1],         # Fertilizers  → Russia, Saudi, Brazil, Canada, China
    6:  [4, 3, 13, 2, 8],          # POL Products → Middle East, Singapore
    7:  [4, 3, 13, 14, 5],         # LNG/LPG      → Middle East, Singapore, Malaysia, Australia
    8:  [5, 17, 1, 19, 7],         # Food Grains  → Australia, Brazil, Canada, Indonesia
    9:  [1, 9, 2, 8, 10],          # Chemicals    → China, Germany, USA, Korea, Japan
    10: [1, 8, 10, 9, 17],         # Steel        → China, Korea, Japan, Germany, Brazil
    11: [9, 2, 10, 8, 1],          # Machinery    → Germany, USA, Japan, Korea, China
    12: [2, 3, 13, 1, 11],         # Textiles     → USA, UAE, Singapore, China, Bangladesh
    13: [5, 17, 18, 1, 7],         # Minerals     → Australia, Brazil, SA, China, Indonesia
    14: [14, 7, 5, 17, 1],         # Timber       → Malaysia, Indonesia, Australia, Brazil
    15: [1, 13, 3, 2, 9],          # General      → China, Singapore, UAE, USA, Germany
}

# Quarterly base volume (million tonnes) per port
PORT_BASE_VOLUME = {
    1: 20,   # JNPT            ~80 MT/yr
    2: 26,   # Kandla          ~104 MT/yr
    3: 38,   # Mundra          ~150 MT/yr  (India's largest private port)
    4: 16,   # Chennai         ~65 MT/yr
    5: 22,   # Vizag           ~88 MT/yr
    6: 21,   # Paradip         ~85 MT/yr
    7: 14,   # Kolkata         ~56 MT/yr
    8: 12,   # Kochi           ~48 MT/yr
    9: 18,   # New Mangalore   ~72 MT/yr
    10: 17,  # Ennore          ~68 MT/yr
}

# Approximate USD value per tonne by commodity
COMMODITY_VALUE_PER_TONNE_USD = {
    1:  550,    # Crude Oil
    2:  120,    # Coal
    3:  1600,   # Containers (avg cargo value)
    4:  80,     # Iron Ore
    5:  280,    # Fertilizers
    6:  650,    # POL Products
    7:  480,    # LNG/LPG
    8:  250,    # Food Grains
    9:  1100,   # Chemicals & Pharma
    10: 700,    # Steel Products
    11: 2400,   # Machinery & Equipment
    12: 3200,   # Textiles & Apparel
    13: 95,     # Minerals & Ores
    14: 175,    # Timber & Wood
    15: 380,    # General Cargo
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _growth_factor(year: int) -> float:
    """Compound annual growth of ~6% from 2019 baseline."""
    return 1.06 ** (year - 2019)


def _covid_factor(year: int, quarter: int) -> float:
    """Simulate COVID-19 trade disruption (2020 Q2 worst)."""
    factors = {
        (2020, 1): 0.94,
        (2020, 2): 0.68,
        (2020, 3): 0.82,
        (2020, 4): 0.94,
        (2021, 1): 0.97,
        (2021, 2): 1.04,
        (2021, 3): 1.08,
        (2021, 4): 1.10,
        (2022, 1): 1.14,  # Post-COVID surge + energy crisis
        (2022, 2): 1.16,
        (2022, 3): 1.13,
        (2022, 4): 1.11,
    }
    return factors.get((year, quarter), 1.0)


def _price_factor(year: int, commodity_id: int) -> float:
    """Simulate commodity price trends (energy spike in 2022)."""
    energy_commodities = {1, 2, 6, 7}
    base = 1 + 0.04 * (year - 2019)  # 4% annual inflation baseline
    if year == 2022 and commodity_id in energy_commodities:
        base *= 1.48   # Ukraine war energy price shock
    elif year == 2023 and commodity_id in energy_commodities:
        base *= 1.20   # Normalising
    return base


def _seasonal_factor(quarter: int) -> float:
    """Q1 and Q4 tend to see slightly higher volumes."""
    return {1: 1.05, 2: 0.97, 3: 0.96, 4: 1.02}[quarter]


# ─────────────────────────────────────────────────────────────────────────────
# Data generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_trade_records() -> pd.DataFrame:
    """
    Generate ~6,000–8,000 realistic quarterly trade records
    for 10 Indian ports across 2019–2024.
    """
    records = []
    record_id = 1

    for year in range(2019, 2025):
        for quarter in range(1, 5):
            growth  = _growth_factor(year)
            covid   = _covid_factor(year, quarter)
            season  = _seasonal_factor(quarter)

            for port in PORTS:
                port_id     = port["id"]
                base_vol    = PORT_BASE_VOLUME[port_id]
                affinities  = PORT_COMMODITY_AFFINITY[port_id]

                for commodity_id, weight in affinities:
                    # Quarterly volume for this port-commodity slot
                    total_vol = base_vol * weight * growth * covid * season
                    total_vol *= np.random.uniform(0.88, 1.12)   # noise

                    # Select 2–4 trading countries
                    country_pool = COMMODITY_COUNTRY_AFFINITY.get(commodity_id, [1, 2, 3])
                    n_countries  = np.random.randint(2, min(5, len(country_pool) + 1))
                    sel_countries = np.random.choice(country_pool, size=n_countries, replace=False)

                    # Distribute volume across selected countries
                    c_weights = np.random.dirichlet(np.ones(n_countries))
                    imp_p, exp_p = COMMODITY_TRADE_TENDENCY[commodity_id]

                    for i, country_id in enumerate(sel_countries):
                        c_vol = total_vol * c_weights[i]

                        for trade_type, share in [("Import", imp_p), ("Export", exp_p)]:
                            vol = c_vol * share
                            if vol < 0.05:
                                continue

                            # Apply some extra noise
                            vol *= np.random.uniform(0.90, 1.10)

                            # Value calculation
                            pf   = _price_factor(year, commodity_id)
                            vpt  = COMMODITY_VALUE_PER_TONNE_USD[commodity_id]
                            # vol is in MT; 1 MT = 1_000_000 tonnes
                            value_usd_million = round(vol * 1_000_000 * vpt * pf / 1_000_000, 2)

                            records.append({
                                "id":               record_id,
                                "port_id":          port_id,
                                "commodity_id":     commodity_id,
                                "country_id":       int(country_id),
                                "year":             year,
                                "quarter":          quarter,
                                "trade_type":       trade_type,
                                "volume_mt":        round(vol, 4),
                                "value_usd_million": value_usd_million,
                            })
                            record_id += 1

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# Database creation
# ─────────────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS ports (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL,
    code      TEXT    NOT NULL,
    city      TEXT,
    state     TEXT,
    lat       REAL,
    lon       REAL,
    port_type TEXT
);

CREATE TABLE IF NOT EXISTS commodities (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    category TEXT
);

CREATE TABLE IF NOT EXISTS countries (
    id     INTEGER PRIMARY KEY,
    name   TEXT NOT NULL,
    code   TEXT,
    region TEXT
);

CREATE TABLE IF NOT EXISTS trade_records (
    id                INTEGER PRIMARY KEY,
    port_id           INTEGER NOT NULL,
    commodity_id      INTEGER NOT NULL,
    country_id        INTEGER NOT NULL,
    year              INTEGER NOT NULL,
    quarter           INTEGER NOT NULL,
    trade_type        TEXT    NOT NULL,
    volume_mt         REAL    NOT NULL,
    value_usd_million REAL    NOT NULL,
    FOREIGN KEY (port_id)      REFERENCES ports(id),
    FOREIGN KEY (commodity_id) REFERENCES commodities(id),
    FOREIGN KEY (country_id)   REFERENCES countries(id)
);

CREATE INDEX IF NOT EXISTS idx_trade_year      ON trade_records(year);
CREATE INDEX IF NOT EXISTS idx_trade_port      ON trade_records(port_id);
CREATE INDEX IF NOT EXISTS idx_trade_commodity ON trade_records(commodity_id);
CREATE INDEX IF NOT EXISTS idx_trade_type      ON trade_records(trade_type);
CREATE INDEX IF NOT EXISTS idx_trade_country   ON trade_records(country_id);
"""


def create_database(df_trade: pd.DataFrame) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"  Removed old database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create schema
    cursor.executescript(DDL)
    print("  Schema created.")

    # Insert master data
    conn.executemany(
        "INSERT INTO ports VALUES (:id,:name,:code,:city,:state,:lat,:lon,:port_type)",
        PORTS,
    )
    conn.executemany(
        "INSERT INTO commodities VALUES (:id,:name,:category)",
        COMMODITIES,
    )
    conn.executemany(
        "INSERT INTO countries VALUES (:id,:name,:code,:region)",
        COUNTRIES,
    )
    print(f"  Master data: {len(PORTS)} ports, {len(COMMODITIES)} commodities, {len(COUNTRIES)} countries.")

    # Insert trade records in chunks
    df_trade.to_sql("trade_records", conn, if_exists="append", index=False, chunksize=500)
    print(f"  Trade records inserted: {len(df_trade):,} rows.")

    conn.commit()
    conn.close()
    print(f"  Database saved to: {DB_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Port-Wise Trade Analytics - ETL Pipeline")
    print("=" * 60)

    print("\n[1/2] Generating trade records ...")
    df_trade = generate_trade_records()
    print(f"      Generated {len(df_trade):,} records  |  Years: 2019-2024  |  Ports: 10")

    print("\n[2/2] Writing to SQLite ...")
    create_database(df_trade)

    print("\n[SUCCESS] ETL complete!")
    print(f"    Database: {DB_PATH}")
    print(f"    Records : {len(df_trade):,}")
    total_vol   = df_trade["volume_mt"].sum()
    total_value = df_trade["value_usd_million"].sum()
    print(f"    Total Volume : {total_vol:,.1f} MT")
    print(f"    Total Value  : ${total_value:,.0f} M USD")
    print("=" * 60)


if __name__ == "__main__":
    main()
