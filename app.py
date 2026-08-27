import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from urllib.parse import quote

from data_utils import (
    load_data, apply_filters, build_export_table, build_leaderboards, get_last_refresh_time,
    STATUS_ORDER, STATUS_COLORS, REGION_ORDER,
    CATEGORY_COLORS, ISSUE_FLAG_ORDER, RECORD_CATEGORY_ORDER,
    CLEAN_LABEL, FOLLOWUP_LABEL, ATTENTION_LABEL, UNFLAGGED_LABEL,
)

# ---------------------------------------------------------------- page setup
st.set_page_config(
    page_title="FIMS Dashboard | Berendina MEAL Unit",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
/* Hide Streamlit chrome – keep header so sidebar toggle works */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
    background: transparent;
}

/* Layout */
.main .block-container {
    padding-top: 1.4rem;
    padding-bottom: 2.5rem;
    max-width: 1420px;
}

/* Typography */
html, body, [class*="css"] {
    font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
}

/* Header Layout */
.fims-header {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 16px;
    margin-bottom: 0.8rem;
    padding-bottom: 0.9rem;
    border-bottom: 1px solid rgba(128,128,128,0.18);
    animation: fadeIn 0.6s ease-out;
}

/* Logo Sizing */
.fims-logo {
    height: 100px;
    width: auto;
    object-fit: contain;
    border-radius: 1px;
}

/* Header Text Wrapper */
.fims-header-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.fims-title {
    font-size: 1.85rem;
    font-weight: 750;
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.fims-tagline {
    font-size: 0.98rem;
    font-weight: 550;
    opacity: 0.78;
    letter-spacing: 0.01em;
    margin-top: 1px;
    margin-bottom: 2px;
}

.fims-subtitle {
    font-size: 0.92rem;
    opacity: 0.62;
    font-weight: 500;
}

/* ---------- KPI Cards ---------- */
.kpi-card {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,0.16);
    border-radius: 12px;
    padding: 15px 16px 13px 16px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    animation: slideUpFade 0.55s ease-out both;
}
.kpi-card:hover {
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    transform: translateY(-3px);
}
.kpi-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3.5px;
}
.kpi-label {
    font-size: 0.71rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    opacity: 0.58;
    margin-bottom: 4px;
}
.kpi-value {
    font-size: 1.62rem;
    font-weight: 720;
    letter-spacing: -0.02em;
    line-height: 1.15;
    transition: transform 0.2s ease;
}
.kpi-card:hover .kpi-value {
    transform: scale(1.03);
}
.kpi-sub {
    font-size: 0.72rem;
    opacity: 0.52;
    margin-top: 3px;
}

/* Meaning colours */
.kpi-total::before   { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.kpi-clean::before   { background: linear-gradient(90deg, #22c55e, #4ade80); }
.kpi-open::before    { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.kpi-escalated::before { background: linear-gradient(90deg, #ef4444, #f87171); }
.kpi-closed::before  { background: linear-gradient(90deg, #10b981, #34d399); }
.kpi-rate::before    { background: linear-gradient(90deg, #0ea5e9, #38bdf8); }

.kpi-total .kpi-value   { color: #3b82f6; }
.kpi-clean .kpi-value   { color: #16a34a; }
.kpi-open .kpi-value    { color: #d97706; }
.kpi-escalated .kpi-value { color: #dc2626; }
.kpi-closed .kpi-value  { color: #059669; }
.kpi-rate .kpi-value    { color: #0284c7; }

/* Stagger KPI cards */
.kpi-card:nth-child(1) { animation-delay: 0.05s; }
.kpi-card:nth-child(2) { animation-delay: 0.10s; }
.kpi-card:nth-child(3) { animation-delay: 0.15s; }
.kpi-card:nth-child(4) { animation-delay: 0.20s; }
.kpi-card:nth-child(5) { animation-delay: 0.25s; }
.kpi-card:nth-child(6) { animation-delay: 0.30s; }

/* ---------- Leaderboard ---------- */
.lb-header {
    font-size: 0.95rem;
    font-weight: 650;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.lb-card {
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,0.14);
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 8px;
    transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
    animation: slideUpFade 0.5s ease-out both;
}
.lb-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 14px rgba(0,0,0,0.07);
}
.lb-rank-badge {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.35rem;
    font-weight: 750;
    flex-shrink: 0;
}
.lb-info { flex: 1; min-width: 0; }
.lb-name {
    font-weight: 620;
    font-size: 0.93rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.lb-metric {
    font-size: 0.78rem;
    opacity: 0.65;
    margin-top: 1px;
}

/* Stagger leaderboard cards */
.lb-card:nth-child(1) { animation-delay: 0.08s; }
.lb-card:nth-child(2) { animation-delay: 0.16s; }
.lb-card:nth-child(3) { animation-delay: 0.24s; }

/* Section headers */
.section-header {
    font-size: 1.15rem;
    font-weight: 680;
    margin: 1.55rem 0 0.65rem 0;
    letter-spacing: -0.01em;
    animation: fadeIn 0.5s ease-out;
}

/* Soft divider */
.soft-divider {
    height: 1px;
    background: rgba(128,128,128,0.14);
    margin: 1.35rem 0 0.55rem 0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128,128,128,0.12);
}

/* ---------- Keyframes ---------- */
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}

@keyframes slideUpFade {
    from {
        opacity: 0;
        transform: translateY(14px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Mobile */
@media (max-width: 640px) {
    .kpi-value { font-size: 1.32rem; }
    .fims-title { font-size: 1.45rem; }
    .main .block-container {
        padding-left: 0.7rem;
        padding-right: 0.7rem;
    }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------- Header
st.markdown(
    """
    <div class="fims-header">
        <img src="https://i.imgur.com/bxd87em.jpeg" class="fims-logo" alt="Logo">
        <div class="fims-header-text">
            <div class="fims-title">FIMS Dashboard</div>
            <div class="fims-tagline">Field Issue Management System</div>
            <div class="fims-subtitle">Berendina Development Services (Gte) Ltd. — MEAL Unit</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- load data
records, issues, merged, notes = load_data()
last_refresh = get_last_refresh_time()
st.caption(f"Data last refreshed: **{last_refresh}**")

with st.sidebar:
    st.markdown("### Filters")
    st.caption(f"Last refresh: **{last_refresh}**")

    years = sorted([y for y in records["Year"].dropna().unique().tolist()])
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    months_present = [m for m in month_order if m in records["MonthName"].unique()]

    sel_years = st.multiselect("Year", years, default=[])
    sel_months = st.multiselect("Month", months_present, default=[])

    st.markdown("---")
    sel_regions = st.multiselect("Region", REGION_ORDER, default=[])
    sel_districts = st.multiselect("District", sorted(records["District"].dropna().unique().tolist()), default=[])
    sel_interventions = st.multiselect("Intervention", sorted(records["Intervention"].dropna().unique().tolist()), default=[])
    sel_officers = st.multiselect("MEAL Officer", sorted(records["MEALOfficer"].dropna().unique().tolist()), default=[])
    sel_staff = st.multiselect(
        "Responsible Officer", sorted(records["NameofResponsibleStaff"].dropna().unique().tolist()), default=[]
    )

    st.markdown("---")
    sel_status = st.multiselect("Issue Status", STATUS_ORDER, default=[])
    sel_flag = st.multiselect("Severity Flag", ISSUE_FLAG_ORDER, default=[])

    st.markdown("---")
    st.caption("Need a data refresh or access help?")
    st.caption("Contact MEAL Unit, Berendina Development Services (Gte) Ltd.")

    _contact_msg = "Hi, I'm reaching out about the FIMS Dashboard (data refresh / access)."
    _whatsapp_url = f"https://wa.me/94703370007?text={quote(_contact_msg)}"
    _email_url = f"mailto:Harshanath@bds.berendina.org?subject={quote('FIMS Dashboard')}&body={quote(_contact_msg)}"

    wc1, wc2 = st.columns(2)
    with wc1:
        st.link_button("WhatsApp", _whatsapp_url, use_container_width=True)
    with wc2:
        st.link_button("Email", _email_url, use_container_width=True)

f_records, f_merged = apply_filters(
    records, merged, sel_years, sel_months, sel_regions, sel_districts, sel_interventions,
    sel_officers, sel_staff, sel_status, sel_flag,
)

if f_records.empty:
    st.warning("No records match the selected filters.")
    st.stop()

status_counts = f_merged["Status"].value_counts()
n_issue = int(status_counts.get("Issue", 0))
n_escalated = int(status_counts.get("Escalated", 0))
n_closed = int(status_counts.get("Closed", 0))
n_total_issues = n_issue + n_escalated + n_closed
resolution_rate = (n_closed / n_total_issues * 100) if n_total_issues else 0

records_with_issues = f_merged["RecordID1"].nunique()
clean_visits = f_records["RecordID"].nunique() - records_with_issues

# ---------------------------------------------------------------- KPI row
k1, k2, k3, k4, k5, k6 = st.columns(6)

kpis = [
    (k1, "Total Visits", f"{f_records['RecordID'].nunique():,}", "Intervention visits", "kpi-total"),
    (k2, "Clean", f"{clean_visits:,}", "No issues found", "kpi-clean"),
    (k3, "Open Issues", f"{n_issue:,}", "Not yet attended", "kpi-open"),
    (k4, "Escalated", f"{n_escalated:,}", "Cannot be resolved", "kpi-escalated"),
    (k5, "Closed", f"{n_closed:,}", "Action taken", "kpi-closed"),
    (k6, "Resolution Rate", f"{resolution_rate:.0f}%", "Of all logged issues", "kpi-rate"),
]

for col, label, value, sub, css_class in kpis:
    col.markdown(
        f"""
        <div class="kpi-card {css_class}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- Staff Leaderboard
st.markdown('<div class="section-header">Staff Leaderboard</div>', unsafe_allow_html=True)

all_staff = sorted(f_records["NameofResponsibleStaff"].dropna().unique().tolist())
solvers_df, responders_df = build_leaderboards(f_merged, all_staff)

TOP_N = 3

def render_leaderboard(df: pd.DataFrame, top_n: int = TOP_N):
    ranked = df[df["Rank"].notna()]
    ranked = ranked[ranked["Rank"] <= top_n]
    if ranked.empty:
        st.caption("No one has qualified for ranking yet.")
        return

    for _, row in ranked.iterrows():
        rank = int(row["Rank"])
        if rank == 1:
            badge_content = "🥇"
        elif rank == 2:
            badge_content = "🥈"
        elif rank == 3:
            badge_content = "🥉"
        else:
            badge_content = f"#{rank}"

        st.markdown(
            f"""
            <div class="lb-card">
                <div class="lb-rank-badge">{badge_content}</div>
                <div class="lb-info">
                    <div class="lb-name">{row['NameofResponsibleStaff']}</div>
                    <div class="lb-metric">{row['MetricDisplay']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

lb1, lb2 = st.columns(2)
with lb1:
    st.markdown('<div class="lb-header">⚡ Top Quick Problem Solvers</div>', unsafe_allow_html=True)
    render_leaderboard(solvers_df)
with lb2:
    st.markdown('<div class="lb-header">🤝 Top Best Responders</div>', unsafe_allow_html=True)
    render_leaderboard(responders_df)

with st.expander("View full staff leaderboard"):
    fl1, fl2 = st.columns(2)
    display_cols = {"Rank": "Rank", "NameofResponsibleStaff": "Staff", "MetricDisplay": "Result"}

    def _display_ready(df):
        out = df[list(display_cols)].rename(columns=display_cols).copy()
        out["Rank"] = out["Rank"].apply(lambda r: f"#{int(r)}" if pd.notna(r) else "—")
        return out

    with fl1:
        st.markdown("**Quick Problem Solvers — full ranking**")
        st.dataframe(_display_ready(solvers_df), hide_index=True, use_container_width=True)
    with fl2:
        st.markdown("**Best Responders — full ranking**")
        st.dataframe(_display_ready(responders_df), hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- Charts
st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

# Row 1
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-header">Visits by Region</div>', unsafe_allow_html=True)
    reg_counts = f_records.groupby("Region")["RecordID"].nunique().reset_index(name="Visits")
    fig = px.pie(
        reg_counts, names="Region", values="Visits", hole=0.48,
        category_orders={"Region": REGION_ORDER},
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    # Keep count inside the chart; percentage only on hover
    fig.update_traces(
        textposition="inside",
        textinfo="label+value",
        textfont_size=12,
        hovertemplate="<b>%{label}</b><br>Visits: %{value}<br>Percentage: %{percent}<extra></extra>"
    )
    fig.update_layout(margin=dict(t=8, b=8, l=8, r=8), height=360, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown('<div class="section-header">Intervention Category by Severity</div>', unsafe_allow_html=True)
    sev_counts = (
        f_records.groupby("SeverityCategory")["RecordID"]
        .nunique()
        .reindex(RECORD_CATEGORY_ORDER)
        .dropna()
        .reset_index()
    )
    sev_counts.columns = ["Category", "Records"]
    fig = px.pie(
        sev_counts, names="Category", values="Records", hole=0.48,
        category_orders={"Category": RECORD_CATEGORY_ORDER},
        color="Category", color_discrete_map=CATEGORY_COLORS
    )
    # Only count inside the chart; full description + % on hover
    fig.update_traces(
        textposition="inside",
        textinfo="value",                    # count only
        textfont_size=13,
        hovertemplate="<b>%{label}</b><br>Records: %{value}<br>Percentage: %{percent}<extra></extra>"
    )
    fig.update_layout(
        margin=dict(t=8, b=8, l=8, r=8),
        height=360,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig, use_container_width=True)

# Row 2
c3, c4 = st.columns([1.35, 1])

with c3:
    st.markdown('<div class="section-header">Issues by Region → District → Status</div>', unsafe_allow_html=True)
    sb_df = f_merged.dropna(subset=["Region", "District", "Status"])
    if not sb_df.empty:
        fig = px.sunburst(
            sb_df, path=["Region", "District", "Status"],
            color="Status", color_discrete_map=STATUS_COLORS
        )
        fig.update_traces(textinfo="label+value", insidetextorientation="radial")
        fig.update_layout(margin=dict(t=8, b=8, l=8, r=8), height=420)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No issues logged for the current filter selection.")

with c4:
    st.markdown('<div class="section-header">Issues by Severity</div>', unsafe_allow_html=True)
    sev2_counts = f_merged["Flag"].value_counts().reindex(ISSUE_FLAG_ORDER).dropna().reset_index()
    sev2_counts.columns = ["Flag", "Count"]
    if not sev2_counts.empty:
        fig = px.pie(
            sev2_counts, names="Flag", values="Count", hole=0.48,
            category_orders={"Flag": ISSUE_FLAG_ORDER},
            color="Flag", color_discrete_map=CATEGORY_COLORS
        )
        # Only count inside; description + % on hover; legend at bottom
        fig.update_traces(
            textposition="inside",
            textinfo="value",
            textfont_size=13,
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
        )
        fig.update_layout(
            margin=dict(t=8, b=8, l=8, r=8),
            height=420,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No issues logged for the current filter selection.")

# Row 3
st.markdown('<div class="section-header">Issue Status by Responsible Officer</div>', unsafe_allow_html=True)
staff_status = f_merged.groupby(["NameofResponsibleStaff", "Status"]).size().reset_index(name="Count")
if not staff_status.empty:
    totals = staff_status.groupby("NameofResponsibleStaff")["Count"].sum()
    order = totals.sort_values(ascending=True).index.tolist()

    _local_status_name = {"Issue": "Open", "Escalated": "Escalated", "Closed": "Closed"}
    fig = go.Figure()
    for s in STATUS_ORDER:
        sub = staff_status[staff_status["Status"] == s].set_index("NameofResponsibleStaff").reindex(order).fillna(0)
        fig.add_trace(go.Bar(
            y=order, x=sub["Count"], name=_local_status_name[s], orientation="h",
            marker_color=STATUS_COLORS[s],
            text=[int(v) if v else "" for v in sub["Count"]],
            textposition="inside",
        ))

    for name in order:
        fig.add_annotation(
            y=name, x=totals[name], text=f"<b>{int(totals[name])}</b>",
            showarrow=False, xanchor="left", xshift=6, font=dict(size=12),
        )

    fig.update_layout(
        barmode="stack",
        height=max(400, 30 * len(order)),
        margin=dict(t=10, b=10, l=10, r=45),
        yaxis_title="",
        xaxis_title="Number of issues",
        legend_title="Status",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("No issues logged for the current filter selection.")

# Row 4 – Map
st.markdown('<div class="section-header">Map of Monitoring Visits</div>', unsafe_allow_html=True)
show_names = st.checkbox("Show beneficiary names on map", value=False)
label_kwargs = dict(text="BeneficiaryName") if show_names else {}

map_df = f_records.dropna(subset=["Latitude", "Longitude"]).copy()
map_df["UnsolvedIssuesDisplay"] = map_df["UnsolvedIssues"].replace("", "None")

if not map_df.empty:
    fig = px.scatter_map(
        map_df, lat="Latitude", lon="Longitude", color="MapCategory",
        category_orders={"MapCategory": RECORD_CATEGORY_ORDER},
        color_discrete_map=CATEGORY_COLORS,
        hover_name="BeneficiaryName",
        hover_data={
            "Intervention": True, "GND": True, "UnsolvedIssuesDisplay": True,
            "Region": True, "District": True, "Latitude": False, "Longitude": False, "MapCategory": False
        },
        zoom=6.7, height=560, **label_kwargs,
    )
    fig.update_layout(
        map_style="open-street-map",
        margin=dict(t=0, b=0, l=0, r=0),
        showlegend=False,
    )
    if show_names:
        fig.update_traces(mode="markers+text", textposition="top center", textfont=dict(size=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🟢 Clean Interventions  ·  🟠 Need Follow-up  ·  🔴 Need immediate attention  ·  ⚪ Unflagged")
else:
    st.caption("No geo-tagged records for the current filter selection.")

# Row 5
c5, c6 = st.columns([1.35, 1])

with c5:
    st.markdown('<div class="section-header">Issue Count by Intervention</div>', unsafe_allow_html=True)
    interv_counts = f_merged.groupby(["Intervention", "Flag"]).size().reset_index(name="Issues")
    if not interv_counts.empty:
        order = interv_counts.groupby("Intervention")["Issues"].sum().sort_values().index.tolist()
        fig = px.bar(
            interv_counts, x="Issues", y="Intervention", color="Flag", orientation="h",
            category_orders={"Intervention": order, "Flag": ISSUE_FLAG_ORDER},
            color_discrete_map=CATEGORY_COLORS
        )
        fig.update_layout(
            height=max(380, 28 * len(order)),
            margin=dict(t=8, b=8, l=8, r=8),
            yaxis_title="", barmode="stack",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No issues logged for the current filter selection.")

with c6:
    st.markdown('<div class="section-header">Most Frequent Issue Types</div>', unsafe_allow_html=True)
    top_names = f_merged["IssueName"].value_counts().head(10).index.tolist()
    top_df = (
        f_merged[f_merged["IssueName"].isin(top_names)]
        .groupby(["IssueName", "Flag"])
        .size()
        .reset_index(name="Count")
    )
    if not top_df.empty:
        order = top_df.groupby("IssueName")["Count"].sum().sort_values().index.tolist()
        fig = px.bar(
            top_df, x="Count", y="IssueName", color="Flag", orientation="h",
            category_orders={"IssueName": order, "Flag": ISSUE_FLAG_ORDER},
            color_discrete_map=CATEGORY_COLORS
        )
        fig.update_layout(
            height=380,
            margin=dict(t=8, b=8, l=8, r=8),
            yaxis_title="", barmode="stack",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No issues logged for the current filter selection.")

# Row 6
c7, c8 = st.columns(2)

with c7:
    st.markdown('<div class="section-header">Visits, Issues & Actions Over Time</div>', unsafe_allow_html=True)
    trend_visits = f_records.groupby(f_records["DateOfVisit"].dt.to_period("M")).agg(Visits=("RecordID", "nunique"))
    issues_dated = f_merged.dropna(subset=["DateOfVisit"])
    trend_issues = issues_dated.groupby(issues_dated["DateOfVisit"].dt.to_period("M")).size().rename("Issues")
    closed_dated = f_merged[(f_merged["Status"] == "Closed")].dropna(subset=["Modified"])
    trend_actions = closed_dated.groupby(closed_dated["Modified"].dt.to_period("M")).size().rename("ActionsTaken")

    trend = (
        trend_visits
        .join(trend_issues, how="outer")
        .join(trend_actions, how="outer")
        .fillna(0)
        .reset_index()
    )
    trend = trend.rename(columns={trend.columns[0]: "Period"})
    trend["Period"] = trend["Period"].dt.to_timestamp()
    trend = trend.sort_values("Period")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["Period"], y=trend["Visits"], name="Visits",
        mode="lines+markers", line=dict(color="#3b82f6", width=2.8)
    ))
    fig.add_trace(go.Scatter(
        x=trend["Period"], y=trend["Issues"], name="Issues logged",
        mode="lines+markers", line=dict(color="#ef4444", width=2.8)
    ))
    fig.add_trace(go.Scatter(
        x=trend["Period"], y=trend["ActionsTaken"], name="Actions taken (Closed)",
        mode="lines+markers", line=dict(color="#22c55e", width=2.8)
    ))
    fig.update_layout(
        height=380,
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(orientation="h", y=1.12),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

with c8:
    st.markdown('<div class="section-header">Resolution Rate by Region</div>', unsafe_allow_html=True)
    reg_status = f_merged.groupby(["Region", "Status"]).size().unstack(fill_value=0)
    for s in STATUS_ORDER:
        if s not in reg_status.columns:
            reg_status[s] = 0
    reg_status["Total"] = reg_status[STATUS_ORDER].sum(axis=1)
    reg_status = reg_status[reg_status["Total"] > 0].reindex([r for r in REGION_ORDER if r in reg_status.index])
    if not reg_status.empty:
        for s in STATUS_ORDER:
            reg_status[f"{s}_pct"] = reg_status[s] / reg_status["Total"] * 100
        fig = go.Figure()

        # Custom labels for the legend
        status_display_names = {"Issue": "Open", "Escalated": "Escalated", "Closed": "Closed"}

        for s in STATUS_ORDER:
            fig.add_trace(go.Bar(
                y=reg_status.index, 
                x=reg_status[f"{s}_pct"], 
                name=status_display_names.get(s, s), # Uses 'Open' instead of 'Issue'
                orientation="h", 
                marker_color=STATUS_COLORS[s]
            ))
        fig.update_layout(
            barmode="stack",
            height=380,
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis_title="% of issues",
            legend_title="Status",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No issues logged for the current filter selection.")
        
# Staff type
st.markdown('<div class="section-header">Visits by Responsible Staff Type (CDC / YDC)</div>', unsafe_allow_html=True)
type_counts = f_records.groupby("ResponsibleStaff")["RecordID"].nunique().reset_index(name="Visits")
fig = px.bar(
    type_counts, x="ResponsibleStaff", y="Visits", color="ResponsibleStaff",
    color_discrete_sequence=px.colors.qualitative.Pastel
)
fig.update_layout(
    height=320,
    margin=dict(t=8, b=8, l=8, r=8),
    showlegend=False,
    xaxis_title="",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, use_container_width=True)

# Data quality
with st.expander("Data quality notes"):
    has_duplicates = notes["duplicate_records_dropped"] > 0
    has_orphans = not notes["orphan_issues"].empty
    has_unflagged = bool(notes["unflagged_issue_texts"])

    if not (has_duplicates or has_orphans or has_unflagged):
        st.write("No data quality issues detected — no duplicates, no orphaned records, no unflagged issues.")
    else:
        if has_duplicates:
            st.write(f"- {notes['duplicate_records_dropped']} duplicate Record ID row(s) were dropped (kept first occurrence).")

        if has_orphans:
            st.write(
                f"- {len(notes['orphan_issues'])} issue row(s) reference a RecordID that doesn't exist in the Records list "
                "(likely deleted/mistyped records or test entries). These were excluded from the dashboard. "
                "Recommend removing them from SharePoint:"
            )
            st.dataframe(notes["orphan_issues"], use_container_width=True, hide_index=True)

        if has_unflagged:
            st.write(
                "- These issue texts didn't match the Issue-to-Flag mapping sheet, so they are shown as **Unflagged** "
                "(likely a mismatched entry in SharePoint):"
            )
            st.write(", ".join(f"`{t}`" for t in notes["unflagged_issue_texts"]))

# Explore & Export
st.markdown('<div class="section-header">Explore & Export Data</div>', unsafe_allow_html=True)
search = st.text_input("Search (beneficiary, staff, intervention, district, issue text, comment)", "")

export_df = build_export_table(f_records, f_merged)
if search:
    s = search.strip().lower()
    mask = export_df.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False)).any(axis=1)
    export_df = export_df[mask]

st.dataframe(export_df, use_container_width=True)
st.download_button(
    "Download filtered data as CSV",
    data=export_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="fims_dashboard_export.csv",
    mime="text/csv",
)

st.caption("FIMS Dashboard — Berendina Development Services (Gte) Ltd., MEAL Unit. Internal use only.")