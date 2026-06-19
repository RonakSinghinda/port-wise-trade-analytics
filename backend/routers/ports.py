"""
routers/ports.py — Port-related API endpoints.
"""
from typing import List
from fastapi import APIRouter, HTTPException
from backend.database import get_connection
from backend.schemas import Port, PortSummary

router = APIRouter()


@router.get("/", response_model=List[Port], summary="List all ports")
def list_ports():
    """Return all 10 major Indian ports with geographic coordinates."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM ports ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/summary", response_model=List[PortSummary], summary="Port performance summary")
def port_summary(year: int = None):
    """Aggregate trade metrics per port, optionally filtered by year."""
    conn = get_connection()
    year_filter = "WHERE t.year = :year" if year else ""

    sql = f"""
        SELECT
            p.id                                      AS port_id,
            p.name                                    AS port_name,
            ROUND(SUM(t.volume_mt), 2)                AS total_volume_mt,
            ROUND(SUM(t.value_usd_million), 2)        AS total_value_usd_million,
            ROUND(SUM(CASE WHEN t.trade_type='Import' THEN t.volume_mt ELSE 0 END), 2) AS import_volume_mt,
            ROUND(SUM(CASE WHEN t.trade_type='Export' THEN t.volume_mt ELSE 0 END), 2) AS export_volume_mt,
            (
                SELECT c.name FROM trade_records tc
                JOIN commodities c ON c.id = tc.commodity_id
                WHERE tc.port_id = p.id {('AND tc.year = ' + str(year)) if year else ''}
                GROUP BY tc.commodity_id ORDER BY SUM(tc.volume_mt) DESC LIMIT 1
            ) AS top_commodity,
            (
                SELECT co.name FROM trade_records tc
                JOIN countries co ON co.id = tc.country_id
                WHERE tc.port_id = p.id {('AND tc.year = ' + str(year)) if year else ''}
                GROUP BY tc.country_id ORDER BY SUM(tc.volume_mt) DESC LIMIT 1
            ) AS top_country
        FROM ports p
        JOIN trade_records t ON t.port_id = p.id
        {year_filter}
        GROUP BY p.id, p.name
        ORDER BY total_volume_mt DESC
    """
    params = {"year": year} if year else {}
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/{port_id}", response_model=Port, summary="Get port details")
def get_port(port_id: int):
    """Return metadata for a single port."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM ports WHERE id = ?", (port_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"Port {port_id} not found")
    return dict(row)
