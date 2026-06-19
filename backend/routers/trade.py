"""
routers/trade.py — Trade volume / trend endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter
from backend.database import get_connection
from backend.schemas import TradeTrend, CommodityBreakdown, CountryTrade

router = APIRouter()


@router.get("/trend", response_model=List[TradeTrend], summary="Quarterly trade trend")
def trade_trend(
    port_id: Optional[int] = None,
    commodity_id: Optional[int] = None,
    trade_type: Optional[str] = None,
):
    """
    Return quarterly aggregated volume and value.
    Supports optional filters: port, commodity, trade_type (Import/Export).
    """
    filters, params = [], {}
    if port_id:
        filters.append("port_id = :port_id"); params["port_id"] = port_id
    if commodity_id:
        filters.append("commodity_id = :commodity_id"); params["commodity_id"] = commodity_id
    if trade_type:
        filters.append("trade_type = :trade_type"); params["trade_type"] = trade_type

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT
            year,
            quarter,
            trade_type,
            ROUND(SUM(volume_mt), 3)          AS total_volume_mt,
            ROUND(SUM(value_usd_million), 2)  AS total_value_usd_million
        FROM trade_records
        {where}
        GROUP BY year, quarter, trade_type
        ORDER BY year, quarter, trade_type
    """
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/commodities", response_model=List[CommodityBreakdown], summary="Commodity breakdown")
def commodity_breakdown(
    port_id: Optional[int] = None,
    year: Optional[int] = None,
    trade_type: Optional[str] = None,
):
    """Aggregate volume and value per commodity, with optional filters."""
    filters, params = [], {}
    if port_id:
        filters.append("t.port_id = :port_id"); params["port_id"] = port_id
    if year:
        filters.append("t.year = :year"); params["year"] = year
    if trade_type:
        filters.append("t.trade_type = :trade_type"); params["trade_type"] = trade_type

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT
            c.name                              AS commodity_name,
            c.category,
            ROUND(SUM(t.volume_mt), 3)          AS total_volume_mt,
            ROUND(SUM(t.value_usd_million), 2)  AS total_value_usd_million,
            t.trade_type
        FROM trade_records t
        JOIN commodities c ON c.id = t.commodity_id
        {where}
        GROUP BY c.id, c.name, c.category, t.trade_type
        ORDER BY total_volume_mt DESC
    """
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/countries", response_model=List[CountryTrade], summary="Country-wise trade")
def country_trade(
    port_id: Optional[int] = None,
    year: Optional[int] = None,
    trade_type: Optional[str] = None,
    limit: int = 20,
):
    """Top trading partners by volume, with optional filters."""
    filters, params = [], {}
    if port_id:
        filters.append("t.port_id = :port_id"); params["port_id"] = port_id
    if year:
        filters.append("t.year = :year"); params["year"] = year
    if trade_type:
        filters.append("t.trade_type = :trade_type"); params["trade_type"] = trade_type

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT
            co.name                             AS country_name,
            co.region,
            ROUND(SUM(t.volume_mt), 3)          AS total_volume_mt,
            ROUND(SUM(t.value_usd_million), 2)  AS total_value_usd_million
        FROM trade_records t
        JOIN countries co ON co.id = t.country_id
        {where}
        GROUP BY co.id, co.name, co.region
        ORDER BY total_volume_mt DESC
        LIMIT :limit
    """
    params["limit"] = limit
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
