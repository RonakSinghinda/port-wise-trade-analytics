import streamlit as pd_st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import sqlite3
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────
pd_st.set_page_config(
    page_title="Port-Wise Trade Analytics Portal",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS for Premium Look & Custom Theme (Aesthetic Styling)
# ─────────────────────────────────────────────────────────────────────────────
pd_st.markdown("""
<style>
    /* Global Styling */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Title Styling */
    .dashboard-title {
        font-weight: 800;
        background: linear-gradient(90deg, #58a6ff 0%, #bc8cff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    
    .dashboard-subtitle {
        color: #8b949e;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #161b22 0%, #21262d 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: #58a6ff;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f0f6fc;
        margin-top: 0.25rem;
    }
    .metric-subtext {
        font-size: 0.8rem;
        color: #58a6ff;
        margin-top: 0.5rem;
    }
    
    /* API Status indicator */
    .status-pill-api {
        background-color: #1f6feb;
        color: #f0f6fc;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-pill-db {
        background-color: #d29922;
        color: #f0f6fc;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Data Access Layer: API-driven with SQLite Fallback
# ─────────────────────────────────────────────────────────────────────────────
API_BASE_URL = "http://localhost:8000/api"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trade_analytics.db"

@pd_st.cache_data
def check_api_connection():
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=1.5)
        if response.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pass
    return False

# Hybrid fetcher functions to retrieve data regardless of backend API running status
def fetch_overview_stats(use_api):
    if use_api:
        try:
            return requests.get(f"{API_BASE_URL}/analytics/overview").json()
        except Exception:
            pass
    # Fallback to direct SQLite read
    conn = sqlite3.connect(str(DB_PATH))
    stats = conn.execute("""
        SELECT
            SUM(volume_mt) AS total_volume_mt,
            SUM(value_usd_million) AS total_value_usd_million,
            COUNT(*) AS total_records,
            COUNT(DISTINCT port_id) AS active_ports,
            COUNT(DISTINCT year) AS years_covered
        FROM trade_records
    """).fetchone()
    
    top_port = conn.execute("""
        SELECT p.name FROM trade_records t JOIN ports p ON p.id = t.port_id
        GROUP BY t.port_id ORDER BY SUM(t.volume_mt) DESC LIMIT 1
    """).fetchone()[0]
    
    top_commodity = conn.execute("""
        SELECT c.name FROM trade_records t JOIN commodities c ON c.id = t.commodity_id
        GROUP BY t.commodity_id ORDER BY SUM(t.volume_mt) DESC LIMIT 1
    """).fetchone()[0]
    
    top_country = conn.execute("""
        SELECT co.name FROM trade_records t JOIN countries co ON co.id = t.country_id
        GROUP BY t.country_id ORDER BY SUM(t.volume_mt) DESC LIMIT 1
    """).fetchone()[0]
    conn.close()
    
    return {
        "total_volume_mt": stats[0],
        "total_value_usd_million": stats[1],
        "total_records": stats[2],
        "active_ports": stats[3],
        "years_covered": stats[4],
        "top_port": top_port,
        "top_commodity": top_commodity,
        "top_country": top_country
    }

def fetch_ports(use_api):
    if use_api:
        try:
            return pd.DataFrame(requests.get(f"{API_BASE_URL}/ports/").json())
        except Exception:
            pass
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("SELECT * FROM ports", conn)
    conn.close()
    return df

def fetch_ports_summary(use_api, year=None):
    if use_api:
        try:
            params = {"year": year} if year else {}
            return pd.DataFrame(requests.get(f"{API_BASE_URL}/ports/summary", params=params).json())
        except Exception:
            pass
    conn = sqlite3.connect(str(DB_PATH))
    year_filter = f"WHERE t.year = {year}" if year else ""
    sql = f"""
        SELECT
            p.id AS port_id,
            p.name AS port_name,
            ROUND(SUM(t.volume_mt), 2) AS total_volume_mt,
            ROUND(SUM(t.value_usd_million), 2) AS total_value_usd_million,
            ROUND(SUM(CASE WHEN t.trade_type='Import' THEN t.volume_mt ELSE 0 END), 2) AS import_volume_mt,
            ROUND(SUM(CASE WHEN t.trade_type='Export' THEN t.volume_mt ELSE 0 END), 2) AS export_volume_mt,
            (SELECT c.name FROM trade_records tc JOIN commodities c ON c.id = tc.commodity_id 
             WHERE tc.port_id = p.id {f'AND tc.year = {year}' if year else ''} 
             GROUP BY tc.commodity_id ORDER BY SUM(tc.volume_mt) DESC LIMIT 1) AS top_commodity,
            (SELECT co.name FROM trade_records tc JOIN countries co ON co.id = tc.country_id 
             WHERE tc.port_id = p.id {f'AND tc.year = {year}' if year else ''} 
             GROUP BY tc.country_id ORDER BY SUM(tc.volume_mt) DESC LIMIT 1) AS top_country
        FROM ports p
        JOIN trade_records t ON t.port_id = p.id
        {year_filter}
        GROUP BY p.id, p.name
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def fetch_trade_trend(use_api, port_id=None, commodity_id=None, trade_type=None):
    if use_api:
        try:
            params = {}
            if port_id: params["port_id"] = port_id
            if commodity_id: params["commodity_id"] = commodity_id
            if trade_type: params["trade_type"] = trade_type
            return pd.DataFrame(requests.get(f"{API_BASE_URL}/trade/trend", params=params).json())
        except Exception:
            pass
    conn = sqlite3.connect(str(DB_PATH))
    filters = []
    if port_id: filters.append(f"port_id = {port_id}")
    if commodity_id: filters.append(f"commodity_id = {commodity_id}")
    if trade_type: filters.append(f"trade_type = '{trade_type}'")
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT year, quarter, trade_type, 
               SUM(volume_mt) AS total_volume_mt, 
               SUM(value_usd_million) AS total_value_usd_million
        FROM trade_records
        {where}
        GROUP BY year, quarter, trade_type
        ORDER BY year, quarter
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def fetch_commodity_breakdown(use_api, port_id=None, year=None, trade_type=None):
    if use_api:
        try:
            params = {}
            if port_id: params["port_id"] = port_id
            if year: params["year"] = year
            if trade_type: params["trade_type"] = trade_type
            return pd.DataFrame(requests.get(f"{API_BASE_URL}/trade/commodities", params=params).json())
        except Exception:
            pass
    conn = sqlite3.connect(str(DB_PATH))
    filters = []
    if port_id: filters.append(f"t.port_id = {port_id}")
    if year: filters.append(f"t.year = {year}")
    if trade_type: filters.append(f"t.trade_type = '{trade_type}'")
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT c.name AS commodity_name, c.category, t.trade_type,
               SUM(t.volume_mt) AS total_volume_mt,
               SUM(t.value_usd_million) AS total_value_usd_million
        FROM trade_records t
        JOIN commodities c ON c.id = t.commodity_id
        {where}
        GROUP BY c.id, c.name, c.category, t.trade_type
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def fetch_country_trade(use_api, port_id=None, year=None, trade_type=None, limit=20):
    if use_api:
        try:
            params = {"limit": limit}
            if port_id: params["port_id"] = port_id
            if year: params["year"] = year
            if trade_type: params["trade_type"] = trade_type
            return pd.DataFrame(requests.get(f"{API_BASE_URL}/trade/countries", params=params).json())
        except Exception:
            pass
    conn = sqlite3.connect(str(DB_PATH))
    filters = []
    if port_id: filters.append(f"t.port_id = {port_id}")
    if year: filters.append(f"t.year = {year}")
    if trade_type: filters.append(f"t.trade_type = '{trade_type}'")
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT co.name AS country_name, co.region,
               SUM(t.volume_mt) AS total_volume_mt,
               SUM(t.value_usd_million) AS total_value_usd_million
        FROM trade_records t
        JOIN countries co ON co.id = t.country_id
        {where}
        GROUP BY co.id, co.name, co.region
        ORDER BY total_volume_mt DESC
        LIMIT {limit}
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def fetch_region_breakdown(use_api, year=None, trade_type=None):
    if use_api:
        try:
            params = {}
            if year: params["year"] = year
            if trade_type: params["trade_type"] = trade_type
            return pd.DataFrame(requests.get(f"{API_BASE_URL}/analytics/region-breakdown", params=params).json())
        except Exception:
            pass
    conn = sqlite3.connect(str(DB_PATH))
    filters = ["1=1"]
    if year: filters.append(f"t.year = {year}")
    if trade_type: filters.append(f"t.trade_type = '{trade_type}'")
    sql = f"""
        SELECT co.region,
               SUM(t.volume_mt) AS total_volume_mt,
               SUM(t.value_usd_million) AS total_value_usd_million
        FROM trade_records t
        JOIN countries co ON co.id = t.country_id
        WHERE {' AND '.join(filters)}
        GROUP BY co.region
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def fetch_raw_data_explorer(port_id=None, commodity_id=None, year=None, trade_type=None):
    conn = sqlite3.connect(str(DB_PATH))
    filters = []
    if port_id: filters.append(f"t.port_id = {port_id}")
    if commodity_id: filters.append(f"t.commodity_id = {commodity_id}")
    if year: filters.append(f"t.year = {year}")
    if trade_type: filters.append(f"t.trade_type = '{trade_type}'")
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    
    sql = f"""
        SELECT 
            t.year AS Year,
            'Q' || t.quarter AS Quarter,
            p.name AS Port,
            p.code AS "Port Code",
            p.state AS State,
            c.name AS Commodity,
            c.category AS Category,
            co.name AS Country,
            co.region AS Region,
            t.trade_type AS "Trade Type",
            ROUND(t.volume_mt, 3) AS "Volume (Million Tonnes)",
            ROUND(t.value_usd_million, 2) AS "Value (USD Millions)"
        FROM trade_records t
        JOIN ports p ON p.id = t.port_id
        JOIN commodities c ON c.id = t.commodity_id
        JOIN countries co ON co.id = t.country_id
        {where}
        ORDER BY Year DESC, Quarter DESC, "Volume (Million Tonnes)" DESC
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ─────────────────────────────────────────────────────────────────────────────
# Initialize Connection Mode
# ─────────────────────────────────────────────────────────────────────────────
api_online = check_api_connection()

# Sidebar Setup
with pd_st.sidebar:
    pd_st.image("https://img.icons8.com/color/180/cargo-ship.png", width=90)
    pd_st.markdown("<h2 style='margin-top:0;'>Port Analytics</h2>", unsafe_allow_html=True)
    
    # Mode indicator
    if api_online:
        pd_st.markdown('<span class="status-pill-api">⚡ FastAPI Backend Connected</span>', unsafe_allow_html=True)
    else:
        pd_st.markdown('<span class="status-pill-db">📂 Direct Database Access</span>', unsafe_allow_html=True)
        pd_st.caption("Tip: Start the FastAPI server (`python backend/main.py`) to run in API mode.")
        
    pd_st.markdown("---")
    
    # Navigation menu
    menu_selection = pd_st.radio(
        "Navigation",
        ["Overview Dashboard", "Port Performance", "Commodity Analysis", "Global Partners", "Raw Data Explorer"]
    )
    
    pd_st.markdown("---")
    pd_st.markdown("### 📊 Metadata Details")
    pd_st.info("""
    This interactive dashboard analyzes cargo trade traffic across 10 major Indian ports. 
    It tracks volume in **Million Tonnes (MT)** and value in **USD Millions**.
    """)
    pd_st.caption("Build Version 1.0.0 | MIT License")

# ─────────────────────────────────────────────────────────────────────────────
# Page 1: Overview Dashboard
# ─────────────────────────────────────────────────────────────────────────────
if menu_selection == "Overview Dashboard":
    pd_st.markdown("<div class='dashboard-title'>Port-Wise Trade Analytics</div>", unsafe_allow_html=True)
    pd_st.markdown("<div class='dashboard-subtitle'>Interactive Overview of India's Maritime Trade Operations (2019-2024)</div>", unsafe_allow_html=True)
    
    # Load Stats
    stats = fetch_overview_stats(api_online)
    
    # KPI Grid
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = pd_st.columns(4)
    
    with kpi_col1:
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Cargo Volume</div>
            <div class="metric-value">{stats['total_volume_mt']:,.1f} MT</div>
            <div class="metric-subtext">Across {stats['years_covered']} Years</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_col2:
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Trade Value</div>
            <div class="metric-value">${stats['total_value_usd_million']:,.0f}M</div>
            <div class="metric-subtext">In USD valuation</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_col3:
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Active Cargo Ports</div>
            <div class="metric-value">{stats['active_ports']}</div>
            <div class="metric-subtext">Major & Private Ports</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_col4:
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Top Hub by Volume</div>
            <div class="metric-value" style="font-size: 1.4rem; padding-top:0.4rem;">{stats['top_port'].split('(')[0]}</div>
            <div class="metric-subtext">Leading volume handler</div>
        </div>
        """, unsafe_allow_html=True)
        
    pd_st.markdown("###")
    
    # Row 2: Maps and Distribution Chart
    col_map, col_dist = pd_st.columns([3, 2])
    
    with col_map:
        pd_st.subheader("📍 Major Indian Ports & Cargo Density")
        
        # Load Ports
        ports_df = fetch_ports(api_online)
        ports_summary_df = fetch_ports_summary(api_online)
        
        map_data = pd.merge(ports_df, ports_summary_df, left_on="id", right_on="port_id")
        
        fig_map = px.scatter_mapbox(
            map_data,
            lat="lat",
            lon="lon",
            size="total_volume_mt",
            color="port_type",
            hover_name="name",
            hover_data={
                "lat": False, "lon": False, "id": False, "port_id": False,
                "total_volume_mt": ":,.1f MT",
                "total_value_usd_million": ":,$2f M",
                "city": True,
                "state": True
            },
            color_discrete_sequence=px.colors.qualitative.Pastel,
            size_max=35,
            zoom=4.2,
            mapbox_style="carto-darkmatter",
            height=480
        )
        fig_map.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(22, 27, 34, 0.8)",
                bordercolor="#30363d",
                borderwidth=1
            )
        )
        pd_st.plotly_chart(fig_map, use_container_width=True)

    with col_dist:
        pd_st.subheader("⚖️ Import vs Export Ratio")
        
        # Get overall trend data for import/export
        trend_df = fetch_trade_trend(api_online)
        summary_im_ex = trend_df.groupby("trade_type")[["total_volume_mt", "total_value_usd_million"]].sum().reset_index()
        
        fig_pie = px.pie(
            summary_im_ex,
            values="total_volume_mt",
            names="trade_type",
            color="trade_type",
            color_discrete_map={"Import": "#1f6feb", "Export": "#238636"},
            hole=0.45,
            height=400
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
        )
        pd_st.plotly_chart(fig_pie, use_container_width=True)
        
        # Micro KPI under the pie
        net_trade_vol = summary_im_ex.loc[summary_im_ex["trade_type"]=="Import", "total_volume_mt"].values[0] - \
                        summary_im_ex.loc[summary_im_ex["trade_type"]=="Export", "total_volume_mt"].values[0]
        pd_st.markdown(f"""
        <div style="background-color:#161b22; border:1px solid #30363d; border-radius:8px; padding:10px; text-align:center;">
            <span style="color:#8b949e; font-size:0.8rem; font-weight:600; text-transform:uppercase;">Volume Trade Balance Gap</span><br/>
            <span style="color:#e1e4e8; font-size:1.2rem; font-weight:700;">{abs(net_trade_vol):,.1f} MT ({"Net Import" if net_trade_vol > 0 else "Net Export"})</span>
        </div>
        """, unsafe_allow_html=True)

    # Row 3: Trade Growth Over Time
    pd_st.subheader("📈 Trade Trends Over Time (Quarterly volume & USD Value)")
    
    # Aggregate quarterly data
    q_trend = trend_df.groupby(["year", "quarter"])[["total_volume_mt", "total_value_usd_million"]].sum().reset_index()
    q_trend["Period"] = q_trend["year"].astype(str) + " Q" + q_trend["quarter"].astype(str)
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Bar(
        x=q_trend["Period"],
        y=q_trend["total_volume_mt"],
        name="Volume (MT)",
        marker_color="#1f6feb",
        opacity=0.75,
        yaxis="y"
    ))
    
    fig_line.add_trace(go.Scatter(
        x=q_trend["Period"],
        y=q_trend["total_value_usd_million"],
        name="Value (USD Millions)",
        line=dict(color="#d29922", width=3, shape="spline"),
        yaxis="y2"
    ))
    
    fig_line.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(
            title="Volume (Million Tonnes)",
            titlefont=dict(color="#1f6feb"),
            tickfont=dict(color="#1f6feb"),
            gridcolor="#21262d"
        ),
        yaxis2=dict(
            title="Value (USD Millions)",
            titlefont=dict(color="#d29922"),
            tickfont=dict(color="#d29922"),
            overlaying="y",
            side="right"
        ),
        xaxis=dict(gridcolor="#21262d", tickangle=-45)
    )
    pd_st.plotly_chart(fig_line, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Page 2: Port Performance
# ─────────────────────────────────────────────────────────────────────────────
elif menu_selection == "Port Performance":
    pd_st.markdown("<div class='dashboard-title'>Port Performance Metrics</div>", unsafe_allow_html=True)
    pd_st.markdown("<div class='dashboard-subtitle'>Deep Dive analysis of individual Indian Port capacities & trade profiles</div>", unsafe_allow_html=True)
    
    ports_df = fetch_ports(api_online)
    
    # Port Selector
    selected_port_name = pd_st.selectbox("Select Port", ports_df["name"].tolist())
    selected_port_row = ports_df[ports_df["name"] == selected_port_name].iloc[0]
    selected_port_id = int(selected_port_row["id"])
    
    # Detail metadata
    col_det1, col_det2, col_det3, col_det4 = pd_st.columns(4)
    with col_det1:
        pd_st.markdown(f"**UN/LOCODE:** `{selected_port_row['code']}`")
    with col_det2:
        pd_st.markdown(f"**Location:** {selected_port_row['city']}, {selected_port_row['state']}")
    with col_det3:
        pd_st.markdown(f"**Management:** {selected_port_row['port_type']}")
    with col_det4:
        pd_st.markdown(f"**Coordinates:** {selected_port_row['lat']}, {selected_port_row['lon']}")
        
    pd_st.markdown("---")
    
    # Fetch data specific to this port
    p_trend = fetch_trade_trend(api_online, port_id=selected_port_id)
    p_commodities = fetch_commodity_breakdown(api_online, port_id=selected_port_id)
    p_countries = fetch_country_trade(api_online, port_id=selected_port_id, limit=10)
    
    # Mini stats cards
    m_col1, m_col2, m_col3 = pd_st.columns(3)
    with m_col1:
        total_vol = p_trend["total_volume_mt"].sum()
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Volume Handled</div>
            <div class="metric-value">{total_vol:,.2f} MT</div>
            <div class="metric-subtext">Cumulative (2019-2024)</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col2:
        total_val = p_trend["total_value_usd_million"].sum()
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Trade Value</div>
            <div class="metric-value">${total_val:,.2f}M</div>
            <div class="metric-subtext">Cumulative Valuation</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col3:
        # Import/Export split
        split_df = p_trend.groupby("trade_type")["total_volume_mt"].sum()
        imp_share = (split_df.get("Import", 0) / total_vol) * 100 if total_vol > 0 else 0
        exp_share = (split_df.get("Export", 0) / total_vol) * 100 if total_vol > 0 else 0
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Trade Split (Volume)</div>
            <div class="metric-value" style="font-size: 1.4rem; padding-top: 0.4rem;">
                Imports: {imp_share:.1f}% <br/> Exports: {exp_share:.1f}%
            </div>
            <div class="metric-subtext">Balance Profile</div>
        </div>
        """, unsafe_allow_html=True)
        
    pd_st.markdown("###")
    
    # Tabs for Port Analysis
    tab_trend, tab_comm, tab_dest = pd_st.tabs(["📊 Historical Trends", "📦 Commodity Split", "🌍 Major Trading Partners"])
    
    with tab_trend:
        pd_st.subheader(f"Historical Activity Trend - {selected_port_name}")
        # Group by year for neat chart
        yearly_p = p_trend.groupby(["year", "trade_type"])[["total_volume_mt", "total_value_usd_million"]].sum().reset_index()
        
        fig_port_trend = px.bar(
            yearly_p,
            x="year",
            y="total_volume_mt",
            color="trade_type",
            barmode="group",
            labels={"total_volume_mt": "Volume (Million Tonnes)", "year": "Year", "trade_type": "Direction"},
            color_discrete_map={"Import": "#1f6feb", "Export": "#238636"},
            height=400
        )
        fig_port_trend.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d")
        )
        pd_st.plotly_chart(fig_port_trend, use_container_width=True)

    with tab_comm:
        pd_st.subheader(f"Commodity Mix - {selected_port_name}")
        # Top commodities by volume
        top_comm_port = p_commodities.groupby("commodity_name")[["total_volume_mt", "total_value_usd_million"]].sum().reset_index()
        top_comm_port = top_comm_port.sort_values(by="total_volume_mt", ascending=True).tail(8)
        
        fig_comm_port = px.bar(
            top_comm_port,
            y="commodity_name",
            x="total_volume_mt",
            orientation="h",
            labels={"total_volume_mt": "Volume (Million Tonnes)", "commodity_name": "Commodity"},
            color_discrete_sequence=["#58a6ff"],
            height=400
        )
        fig_comm_port.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d")
        )
        pd_st.plotly_chart(fig_comm_port, use_container_width=True)

    with tab_dest:
        pd_st.subheader(f"Top 10 Global Partners - {selected_port_name}")
        
        fig_partner_port = px.bar(
            p_countries.sort_values(by="total_volume_mt", ascending=True),
            y="country_name",
            x="total_volume_mt",
            orientation="h",
            color="region",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            labels={"total_volume_mt": "Volume (Million Tonnes)", "country_name": "Country", "region": "Region"},
            height=400
        )
        fig_partner_port.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d")
        )
        pd_st.plotly_chart(fig_partner_port, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Page 3: Commodity Analysis
# ─────────────────────────────────────────────────────────────────────────────
elif menu_selection == "Commodity Analysis":
    pd_st.markdown("<div class='dashboard-title'>Commodity Insights</div>", unsafe_allow_html=True)
    pd_st.markdown("<div class='dashboard-subtitle'>Detailed breakdowns of trade flows categorized by cargo and commodity type</div>", unsafe_allow_html=True)
    
    # Fetch general commodities to establish filters
    all_comm_breakdown = fetch_commodity_breakdown(api_online)
    comm_names = sorted(all_comm_breakdown["commodity_name"].unique())
    
    # Selection filter
    selected_commodity = pd_st.selectbox("Select Commodity", comm_names)
    
    # Filters based on selected commodity
    comm_subset = all_comm_breakdown[all_comm_breakdown["commodity_name"] == selected_commodity]
    total_comm_volume = comm_subset["total_volume_mt"].sum()
    total_comm_value = comm_subset["total_value_usd_million"].sum()
    category_name = comm_subset["category"].iloc[0] if len(comm_subset) > 0 else "N/A"
    
    # Headline details
    cc_col1, cc_col2, cc_col3 = pd_st.columns(3)
    with cc_col1:
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Category Group</div>
            <div class="metric-value">{category_name}</div>
            <div class="metric-subtext">Product Classification</div>
        </div>
        """, unsafe_allow_html=True)
    with cc_col2:
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Volume Shipped</div>
            <div class="metric-value">{total_comm_volume:,.2f} MT</div>
            <div class="metric-subtext">All ports combined</div>
        </div>
        """, unsafe_allow_html=True)
    with cc_col3:
        pd_st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Shipped Value</div>
            <div class="metric-value">${total_comm_value:,.2f}M</div>
            <div class="metric-subtext">USD valuation</div>
        </div>
        """, unsafe_allow_html=True)
        
    pd_st.markdown("###")
    
    col_c_left, col_c_right = pd_st.columns(2)
    
    with col_c_left:
        pd_st.subheader("⚖️ Trade Balance for this Commodity")
        comm_balance = comm_subset.groupby("trade_type")["total_volume_mt"].sum().reset_index()
        fig_comm_pie = px.pie(
            comm_balance,
            values="total_volume_mt",
            names="trade_type",
            color="trade_type",
            color_discrete_map={"Import": "#1f6feb", "Export": "#238636"},
            hole=0.4,
            height=350
        )
        fig_comm_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        pd_st.plotly_chart(fig_comm_pie, use_container_width=True)
        
    with col_c_right:
        pd_st.subheader("🏢 Top Ports Handling this Cargo")
        # To get the ports handling this commodity, query the raw explorer data source
        raw_df_comm = fetch_raw_data_explorer(commodity_id=None)
        filtered_raw = raw_df_comm[raw_df_comm["Commodity"] == selected_commodity]
        port_rank = filtered_raw.groupby("Port")["Volume (Million Tonnes)"].sum().reset_index()
        port_rank = port_rank.sort_values(by="Volume (Million Tonnes)", ascending=True).tail(5)
        
        fig_comm_ports = px.bar(
            port_rank,
            y="Port",
            x="Volume (Million Tonnes)",
            orientation="h",
            color_discrete_sequence=["#bc8cff"],
            height=350
        )
        fig_comm_ports.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d")
        )
        pd_st.plotly_chart(fig_comm_ports, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Page 4: Global Partners
# ─────────────────────────────────────────────────────────────────────────────
elif menu_selection == "Global Partners":
    pd_st.markdown("<div class='dashboard-title'>Global Trading Partners</div>", unsafe_allow_html=True)
    pd_st.markdown("<div class='dashboard-subtitle'>Analyze India's maritime trade corridors and regional partnerships</div>", unsafe_allow_html=True)
    
    # Filters
    col_f1, col_f2 = pd_st.columns(2)
    with col_f1:
        sel_year = pd_st.selectbox("Select Year", [None, 2024, 2023, 2022, 2021, 2020, 2019])
    with col_f2:
        sel_type = pd_st.selectbox("Select Flow Type", [None, "Import", "Export"])
        
    # Fetch Data
    country_df = fetch_country_trade(api_online, year=sel_year, trade_type=sel_type, limit=20)
    region_df = fetch_region_breakdown(api_online, year=sel_year, trade_type=sel_type)
    
    col_reg1, col_reg2 = pd_st.columns(2)
    
    with col_reg1:
        pd_st.subheader("🌍 Regional Trade Distribution")
        fig_region = px.pie(
            region_df,
            values="total_volume_mt",
            names="region",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hole=0.4,
            height=400
        )
        fig_region.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        pd_st.plotly_chart(fig_region, use_container_width=True)
        
    with col_reg2:
        pd_st.subheader("🏆 Top 10 Trading Countries (Volume)")
        top_10_countries = country_df.head(10).sort_values(by="total_volume_mt", ascending=True)
        
        fig_country_bar = px.bar(
            top_10_countries,
            y="country_name",
            x="total_volume_mt",
            orientation="h",
            color="total_value_usd_million",
            color_continuous_scale="Viridis",
            labels={
                "total_volume_mt": "Volume (Million Tonnes)",
                "country_name": "Country",
                "total_value_usd_million": "Value (USD M)"
            },
            height=400
        )
        fig_country_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d")
        )
        pd_st.plotly_chart(fig_country_bar, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Page 5: Raw Data Explorer
# ─────────────────────────────────────────────────────────────────────────────
elif menu_selection == "Raw Data Explorer":
    pd_st.markdown("<div class='dashboard-title'>Trade Data Explorer</div>", unsafe_allow_html=True)
    pd_st.markdown("<div class='dashboard-subtitle'>Search, filter, and extract custom slices of the trade analytics datasets</div>", unsafe_allow_html=True)
    
    # Controls
    col_c1, col_c2, col_c3, col_c4 = pd_st.columns(4)
    
    # Need to load lookup tables for selectors
    ports_df = fetch_ports(api_online)
    all_comm_breakdown = fetch_commodity_breakdown(api_online)
    comm_names = sorted(all_comm_breakdown["commodity_name"].unique())
    
    with col_c1:
        f_port = pd_st.selectbox("Filter Port", [None] + ports_df["name"].tolist())
    with col_c2:
        f_comm = pd_st.selectbox("Filter Commodity", [None] + comm_names)
    with col_c3:
        f_year = pd_st.selectbox("Filter Year", [None, 2024, 2023, 2022, 2021, 2020, 2019])
    with col_c4:
        f_type = pd_st.selectbox("Filter Type", [None, "Import", "Export"])
        
    # Resolve IDs
    port_id_val = None
    if f_port:
        port_id_val = int(ports_df[ports_df["name"] == f_port].iloc[0]["id"])
        
    comm_id_val = None
    if f_comm:
        # Simple lookup connection
        conn_temp = sqlite3.connect(str(DB_PATH))
        c_row = conn_temp.execute("SELECT id FROM commodities WHERE name = ?", (f_comm,)).fetchone()
        if c_row:
            comm_id_val = c_row[0]
        conn_temp.close()
        
    # Query Database
    raw_df = fetch_raw_data_explorer(
        port_id=port_id_val,
        commodity_id=comm_id_val,
        year=f_year,
        trade_type=f_type
    )
    
    # Display Stats
    pd_st.markdown(f"**Found {len(raw_df):,} matching rows.**")
    
    # Render table
    pd_st.dataframe(raw_df, use_container_width=True, height=500)
    
    # Export CSV Option
    csv_data = raw_df.to_csv(index=False).encode('utf-8')
    pd_st.download_button(
        label="📥 Download current slice as CSV",
        data=csv_data,
        file_name="port_trade_export.csv",
        mime="text/csv"
    )
