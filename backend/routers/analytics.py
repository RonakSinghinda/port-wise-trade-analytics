"""
routers/analytics.py — High-level analytics & insight endpoints.
"""
from fastapi import APIRouter
from backend.database import get_connection
from backend.schemas import OverviewStats

router = APIRouter()


@router.get("/overview", response_model=OverviewStats, summary="Overall platform statistics")
def overview():
    """Return headline KPIs across all ports, commodities, and years."""
    conn = get_connection()

    stats = conn.execute("""
        SELECT
            ROUND(SUM(volume_mt), 2)          AS total_volume_mt,
            ROUND(SUM(value_usd_million), 2)  AS total_value_usd_million,
            COUNT(*)                           AS total_records,
            COUNT(DISTINCT port_id)            AS active_ports,
            COUNT(DISTINCT year)               AS years_covered
        FROM trade_records
    """).fetchone()

    top_port = conn.execute("""
        SELECT p.name FROM trade_records t
        JOIN ports p ON p.id = t.port_id
        GROUP BY t.port_id ORDER BY SUM(t.volume_mt) DESC LIMIT 1
    """).fetchone()[0]

    top_commodity = conn.execute("""
        SELECT c.name FROM trade_records t
        JOIN commodities c ON c.id = t.commodity_id
        GROUP BY t.commodity_id ORDER BY SUM(t.volume_mt) DESC LIMIT 1
    """).fetchone()[0]

    top_country = conn.execute("""
        SELECT co.name FROM trade_records t
        JOIN countries co ON co.id = t.country_id
        GROUP BY t.country_id ORDER BY SUM(t.volume_mt) DESC LIMIT 1
    """).fetchone()[0]

    conn.close()
    return {
        **dict(stats),
        "top_port": top_port,
        "top_commodity": top_commodity,
        "top_country": top_country,
    }


@router.get("/top-ports", summary="Top ports by volume or value")
def top_ports(metric: str = "volume", year: int = None, limit: int = 10):
    """
    Return top ports ranked by total trade volume (MT) or value (USD million).
    metric: 'volume' | 'value'
    """
    order_col = "SUM(t.volume_mt)" if metric != "value" else "SUM(t.value_usd_million)"
    year_filter = "AND t.year = :year" if year else ""
    params = {"limit": limit}
    if year:
        params["year"] = year

    sql = f"""
        SELECT
            p.name                              AS port_name,
            p.state,
            p.port_type,
            ROUND(SUM(t.volume_mt), 2)          AS total_volume_mt,
            ROUND(SUM(t.value_usd_million), 2)  AS total_value_usd_million
        FROM trade_records t
        JOIN ports p ON p.id = t.port_id
        WHERE 1=1 {year_filter}
        GROUP BY p.id, p.name, p.state, p.port_type
        ORDER BY {order_col} DESC
        LIMIT :limit
    """
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/trade-balance", summary="Import vs Export balance by year")
def trade_balance(port_id: int = None):
    """Yearly import/export totals, optionally filtered to a specific port."""
    port_filter = "AND t.port_id = :port_id" if port_id else ""
    params = {}
    if port_id:
        params["port_id"] = port_id

    sql = f"""
        SELECT
            t.year,
            t.trade_type,
            ROUND(SUM(t.volume_mt), 2)          AS total_volume_mt,
            ROUND(SUM(t.value_usd_million), 2)  AS total_value_usd_million
        FROM trade_records t
        WHERE 1=1 {port_filter}
        GROUP BY t.year, t.trade_type
        ORDER BY t.year, t.trade_type
    """
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/region-breakdown", summary="Trade breakdown by geographic region")
def region_breakdown(year: int = None, trade_type: str = None):
    """Aggregate trade by country region."""
    filters, params = ["1=1"], {}
    if year:
        filters.append("t.year = :year"); params["year"] = year
    if trade_type:
        filters.append("t.trade_type = :trade_type"); params["trade_type"] = trade_type

    sql = f"""
        SELECT
            co.region,
            ROUND(SUM(t.volume_mt), 2)          AS total_volume_mt,
            ROUND(SUM(t.value_usd_million), 2)  AS total_value_usd_million
        FROM trade_records t
        JOIN countries co ON co.id = t.country_id
        WHERE {' AND '.join(filters)}
        GROUP BY co.region
        ORDER BY total_volume_mt DESC
    """
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
