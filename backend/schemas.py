"""
schemas.py — Pydantic response models for the FastAPI backend.
"""
from typing import List, Optional
from pydantic import BaseModel


# ── Lookup tables ─────────────────────────────────────────────────────────────

class Port(BaseModel):
    id: int
    name: str
    code: str
    city: str
    state: str
    lat: float
    lon: float
    port_type: str


class Commodity(BaseModel):
    id: int
    name: str
    category: str


class Country(BaseModel):
    id: int
    name: str
    code: str
    region: str


# ── Analytics payloads ────────────────────────────────────────────────────────

class PortSummary(BaseModel):
    port_id: int
    port_name: str
    total_volume_mt: float
    total_value_usd_million: float
    import_volume_mt: float
    export_volume_mt: float
    top_commodity: str
    top_country: str


class TradeTrend(BaseModel):
    year: int
    quarter: int
    trade_type: str
    total_volume_mt: float
    total_value_usd_million: float


class CommodityBreakdown(BaseModel):
    commodity_name: str
    category: str
    total_volume_mt: float
    total_value_usd_million: float
    trade_type: Optional[str] = None


class CountryTrade(BaseModel):
    country_name: str
    region: str
    total_volume_mt: float
    total_value_usd_million: float


class OverviewStats(BaseModel):
    total_volume_mt: float
    total_value_usd_million: float
    total_records: int
    active_ports: int
    years_covered: int
    top_port: str
    top_commodity: str
    top_country: str
