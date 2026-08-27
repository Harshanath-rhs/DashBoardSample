"""
Data loading & cleaning for the FIMS Dashboard — Berendina Development
Services (Gte) Ltd., MEAL Unit.

Reads the two SharePoint-exported lists (Monitoring_Records.csv and
Monitoring_Issues.csv) from /data, cleans them, joins them on
RecordID <-> RecordID1, tags every issue with a severity category using
reference/issue_flag_mapping.csv, and computes staff leaderboards.

MONTHLY REFRESH: overwrite the two CSVs in /data (the one-click tool
handles this). No code changes needed unless the SharePoint list
structure itself changes.
"""

from pathlib import Path
import subprocess
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RECORDS_FILE = DATA_DIR / "Monitoring_Records.csv"
ISSUES_FILE = DATA_DIR / "Monitoring_Issues.csv"
FLAG_MAP_FILE = BASE_DIR / "reference" / "issue_flag_mapping.csv"

CACHE_TTL_SECONDS = 600  # 10 minutes

# ---------------------------------------------------------------- status
STATUS_ORDER = ["Issue", "Escalated", "Closed"]
STATUS_COLORS = {
    "Issue": "#EF553B",       # red-orange = open, no action yet
    "Escalated": "#F5A623",   # amber = flagged up, can't be solved by responsible staff
    "Closed": "#2CA02C",      # green = resolved
}

# ---------------------------------------------------------------- severity / category labels
# Single naming scheme used EVERYWHERE in the app - never show raw Red/Amber/Green.
CLEAN_LABEL = "Clean Interventions"
FOLLOWUP_LABEL = "Need Follow-up"
ATTENTION_LABEL = "Need immediate attention"
UNFLAGGED_LABEL = "Unflagged"

CATEGORY_COLORS = {
    CLEAN_LABEL: "#2CA02C",
    FOLLOWUP_LABEL: "#F59E0B",
    ATTENTION_LABEL: "#DC2626",
    UNFLAGGED_LABEL: "#9CA3AF",
}
# order for per-issue charts (an issue itself is never "clean")
ISSUE_FLAG_ORDER = [ATTENTION_LABEL, FOLLOWUP_LABEL, UNFLAGGED_LABEL]
# order for per-record charts / map (a record can be clean)
RECORD_CATEGORY_ORDER = [CLEAN_LABEL, FOLLOWUP_LABEL, ATTENTION_LABEL, UNFLAGGED_LABEL]

_RAW_FLAG_TO_LABEL = {"Red": ATTENTION_LABEL, "Amber": FOLLOWUP_LABEL, "Unflagged": UNFLAGGED_LABEL}

# ---------------------------------------------------------------- region grouping
DISTRICT_TO_REGION = {
    "Kegalle": "NC Region",
    "Anuradhapura": "NC Region",
    "Mullaitivu": "NE Region",
    "Trincomalee": "NE Region",
    "Batticaloa": "NE Region",
    "Nuwara Eliya (Plantation)": "Central Region",
    "Nuwara Eliya (Rural)": "Central Region",
}
REGION_ORDER = ["NC Region", "NE Region", "Central Region"]


def _normalize_status(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "Issue"
    s = raw.strip().lower()
    if s.startswith("esc"):
        return "Escalated"
    if s.startswith("clos") or s.startswith("solv") or s.startswith("resolv"):
        return "Closed"
    return "Issue"


def _severity_from_labels(labels) -> str:
    """Given a list of per-issue category labels tied to one record, decide the
    record's overall category. Precedence: any 'attention' > any 'follow-up' >
    any 'unflagged' > (no issues at all) 'clean'."""
    s = set(labels)
    if ATTENTION_LABEL in s:
        return ATTENTION_LABEL
    if FOLLOWUP_LABEL in s:
        return FOLLOWUP_LABEL
    if UNFLAGGED_LABEL in s:
        return UNFLAGGED_LABEL
    return CLEAN_LABEL


@st.cache_data(show_spinner=False)
def _load_flag_mapping():
    """Returns (pair_map, text_map): (Intervention, IssueText) -> raw Flag
    (Red/Amber), and a fallback IssueText -> Flag map for unambiguous texts."""
    fm = pd.read_csv(FLAG_MAP_FILE)
    fm.columns = [c.strip() for c in fm.columns]
    text_col = [c for c in fm.columns if c.startswith("Issue Statement")][0]
    fm["Intervention"] = fm["Intervention"].astype(str).str.strip()
    fm[text_col] = fm[text_col].astype(str).str.strip()

    pair_map = {}
    text_flags = {}
    for _, row in fm.iterrows():
        pair_map[(row["Intervention"], row[text_col])] = row["Flag"]
        text_flags.setdefault(row[text_col], set()).add(row["Flag"])

    text_map = {t: list(flags)[0] for t, flags in text_flags.items() if len(flags) == 1}
    return pair_map, text_map


def get_last_refresh_time():
    """Best-effort: when was /data last updated in Git history? Falls back to
    file modified time if Git isn't available in this environment."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%d %b %Y, %I:%M %p", "--", "data/"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=5,
        )
        ts = out.stdout.strip()
        if ts:
            return ts
    except Exception:
        pass
    try:
        import datetime
        mtime = max(RECORDS_FILE.stat().st_mtime, ISSUES_FILE.stat().st_mtime)
        return datetime.datetime.fromtimestamp(mtime).strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return "unknown"


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def load_data(records_path: Path = RECORDS_FILE, issues_path: Path = ISSUES_FILE):
    """Load, clean, flag-tag and join the two lists.
    Returns (records_df, issues_df, merged_df, data_quality_notes: dict)."""

    records = pd.read_csv(records_path, encoding="utf-8-sig")
    issues = pd.read_csv(issues_path, encoding="utf-8-sig")
    records.columns = [c.strip() for c in records.columns]
    issues.columns = [c.strip() for c in issues.columns]

    notes = {}

    # ---------------- clean records ----------------
    records["RecordID"] = records["RecordID"].astype(str).str.strip()
    dup_n = int(records.duplicated(subset="RecordID", keep="first").sum())
    notes["duplicate_records_dropped"] = dup_n
    records = records.drop_duplicates(subset="RecordID", keep="first")

    records["DateOfVisit"] = pd.to_datetime(records["DateOfVisit"], format="%m/%d/%Y", errors="coerce")
    records["Year"] = records["DateOfVisit"].dt.year
    records["Month"] = records["DateOfVisit"].dt.month
    records["MonthName"] = records["DateOfVisit"].dt.strftime("%b")

    records["District"] = records["District"].astype(str).str.strip()
    records["Region"] = records["District"].map(DISTRICT_TO_REGION).fillna("Other")

    gps_split = records["GPSCoordinates"].astype(str).str.split(",", n=1, expand=True)
    records["Latitude"] = pd.to_numeric(gps_split[0], errors="coerce")
    records["Longitude"] = pd.to_numeric(gps_split[1], errors="coerce") if gps_split.shape[1] > 1 else pd.NA

    for col in ["MEALOfficer", "NameofResponsibleStaff", "ResponsibleStaff", "Intervention", "BeneficiaryName", "GND"]:
        if col in records.columns:
            records[col] = records[col].astype(str).str.strip()

    # ---------------- clean issues ----------------
    issues["RecordID1"] = issues["RecordID1"].astype(str).str.strip()
    issues["IssueName"] = issues["IssueName"].astype(str).str.strip()
    issues["Status"] = issues["IssueStatus"].apply(_normalize_status)
    issues["Comment"] = issues["Comment"].fillna("").astype(str).str.strip() if "Comment" in issues.columns else ""
    issues["Created"] = pd.to_datetime(issues.get("Created"), format="%m/%d/%Y %I:%M %p", errors="coerce")
    issues["Modified"] = pd.to_datetime(issues.get("Modified"), format="%m/%d/%Y %I:%M %p", errors="coerce")

    valid_ids = set(records["RecordID"])
    is_orphan = ~issues["RecordID1"].isin(valid_ids)
    notes["orphan_issues"] = issues.loc[is_orphan, ["RecordID1", "IssueName", "IssueStatus"]].copy()
    issues = issues.loc[~is_orphan].copy()

    # ---------------- severity flag (renamed labels used everywhere) ----------------
    pair_map, text_map = _load_flag_mapping()
    interv_by_id = records.set_index("RecordID")["Intervention"].to_dict()
    issues["Intervention"] = issues["RecordID1"].map(interv_by_id)

    def _get_flag(row):
        key = (row["Intervention"], row["IssueName"])
        raw = pair_map.get(key) or text_map.get(row["IssueName"], "Unflagged")
        return _RAW_FLAG_TO_LABEL.get(raw, UNFLAGGED_LABEL)

    issues["Flag"] = issues.apply(_get_flag, axis=1)
    notes["unflagged_issue_texts"] = sorted(
        issues.loc[issues["Flag"] == UNFLAGGED_LABEL, "IssueName"].unique().tolist()
    )

    # ---------------- "valid interaction" (comment given + actually edited) ----------------
    issues["ValidInteraction"] = (issues["Comment"] != "") & (issues["Modified"] != issues["Created"])
    issues["DurationMinutes"] = (issues["Modified"] - issues["Created"]).dt.total_seconds() / 60.0

    # ---------------- record-level severity category (all issues, any status) ----------------
    by_record_all = issues.groupby("RecordID1")["Flag"].apply(list)
    records["SeverityCategory"] = records["RecordID"].map(by_record_all).apply(
        lambda v: _severity_from_labels(v) if isinstance(v, list) else CLEAN_LABEL
    )

    # ---------------- map category (only OPEN issues count) ----------------
    open_issues = issues[issues["Status"] == "Issue"]
    by_record_open = open_issues.groupby("RecordID1")["Flag"].apply(list)
    records["MapCategory"] = records["RecordID"].map(by_record_open).apply(
        lambda v: _severity_from_labels(v) if isinstance(v, list) else CLEAN_LABEL
    )
    unsolved_names = open_issues.groupby("RecordID1")["IssueName"].apply(lambda s: ", ".join(s))
    records["UnsolvedIssues"] = records["RecordID"].map(unsolved_names).fillna("")

    # ---------------- join ----------------
    merged = issues.merge(records, left_on="RecordID1", right_on="RecordID", how="left", suffixes=("", "_rec"))

    return records, issues, merged, notes


def apply_filters(records, merged, years, months, regions, districts, interventions, officers, staff, statuses, flags):
    def _f(df):
        out = df
        if years:
            out = out[out["Year"].isin(years)]
        if months:
            out = out[out["MonthName"].isin(months)]
        if regions:
            out = out[out["Region"].isin(regions)]
        if districts:
            out = out[out["District"].isin(districts)]
        if interventions:
            out = out[out["Intervention"].isin(interventions)]
        if officers:
            out = out[out["MEALOfficer"].isin(officers)]
        if staff:
            out = out[out["NameofResponsibleStaff"].isin(staff)]
        return out

    f_records = _f(records)
    f_merged = _f(merged)
    if statuses:
        f_merged = f_merged[f_merged["Status"].isin(statuses)]
    if flags:
        f_merged = f_merged[f_merged["Flag"].isin(flags)]
    return f_records, f_merged


def build_export_table(f_records: pd.DataFrame, f_merged: pd.DataFrame) -> pd.DataFrame:
    """One row per record, with all of that record's issues (name, status, flag)
    rolled up into one column, and officer comments rolled up into a SEPARATE
    column, ready for CSV download."""

    def _fmt_issues(g):
        return "; ".join(f"{r.IssueName} [{r.Status}/{r.Flag}]" for r in g.itertuples())

    def _fmt_comments(g):
        parts = [f"{r.IssueName}: {r.Comment}" for r in g.itertuples() if getattr(r, "Comment", "")]
        return "; ".join(parts)

    if not f_merged.empty:
        issue_rollup = f_merged.groupby("RecordID1").apply(_fmt_issues).rename("Issues (Name [Status/Flag])")
        comment_rollup = f_merged.groupby("RecordID1").apply(_fmt_comments).rename("Officer Comments")
        issue_counts = f_merged.groupby("RecordID1").size().rename("IssueCount")
    else:
        issue_rollup = pd.Series(dtype=str, name="Issues (Name [Status/Flag])")
        comment_rollup = pd.Series(dtype=str, name="Officer Comments")
        issue_counts = pd.Series(dtype=int, name="IssueCount")

    out = f_records.merge(issue_rollup, left_on="RecordID", right_index=True, how="left")
    out = out.merge(comment_rollup, left_on="RecordID", right_index=True, how="left")
    out = out.merge(issue_counts, left_on="RecordID", right_index=True, how="left")
    out["IssueCount"] = out["IssueCount"].fillna(0).astype(int)
    out["Issues (Name [Status/Flag])"] = out["Issues (Name [Status/Flag])"].fillna("No issues")
    out["Officer Comments"] = out["Officer Comments"].fillna("")
    return out


def _format_minutes(total_minutes: float) -> str:
    if total_minutes is None or pd.isna(total_minutes) or total_minutes <= 0:
        return "—"
    total_minutes = int(round(total_minutes))
    days, rem = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


def build_leaderboards(f_merged: pd.DataFrame, all_staff: list) -> tuple:
    """Returns (solvers_df, responders_df). Both have columns:
    NameofResponsibleStaff, Rank (nullable - None means not yet qualified),
    MetricDisplay (str shown on cards/tables), plus type-specific raw columns.

    Solvers: ranked ascending by cumulative time spent on valid, Closed issues
    (faster total time wins). Responders: ranked by how many of their assigned
    issues they've genuinely responded to (Escalated+Closed, valid interaction),
    most responded wins; ties broken by % of their issues responded to.
    Staff with zero qualifying issues get Rank=None (unranked, shown only in
    the full table, never in the top-N spotlight)."""

    valid = f_merged[f_merged["ValidInteraction"]]

    # ---------------- Quick Problem Solvers: ascending cumulative time, Closed only ----------------
    closed_valid = valid[valid["Status"] == "Closed"]
    solver_agg = closed_valid.groupby("NameofResponsibleStaff").agg(
        Count=("DurationMinutes", "count"),
        CumulativeMinutes=("DurationMinutes", "sum"),
    )
    solver_agg = solver_agg.reindex(all_staff).fillna(0)
    solver_agg["MetricDisplay"] = solver_agg.apply(
        lambda r: f"{int(r['Count'])} issue(s) · {_format_minutes(r['CumulativeMinutes'])}" if r["Count"] > 0 else "Not ranked yet",
        axis=1,
    )
    s_qualified = solver_agg[solver_agg["Count"] > 0].sort_values("CumulativeMinutes", ascending=True)
    s_unqualified = solver_agg[solver_agg["Count"] == 0].sort_index()
    s_qualified = s_qualified.reset_index().rename(columns={"index": "NameofResponsibleStaff"})
    s_unqualified = s_unqualified.reset_index().rename(columns={"index": "NameofResponsibleStaff"})
    s_qualified["Rank"] = range(1, len(s_qualified) + 1)
    s_unqualified["Rank"] = None
    solvers = pd.concat([s_qualified, s_unqualified], ignore_index=True)

    # ---------------- Best Responders: most issues responded to, tie-break % responded ----------------
    responded_valid = valid[valid["Status"].isin(["Escalated", "Closed"])]
    total_counts = f_merged.groupby("NameofResponsibleStaff").size()
    responded_counts = responded_valid.groupby("NameofResponsibleStaff").size()

    resp_agg = pd.DataFrame(index=all_staff)
    resp_agg["Total"] = total_counts.reindex(all_staff).fillna(0)
    resp_agg["Responded"] = responded_counts.reindex(all_staff).fillna(0)
    resp_agg["Percentage"] = resp_agg.apply(
        lambda r: (r["Responded"] / r["Total"] * 100) if r["Total"] > 0 else 0, axis=1
    )
    resp_agg["MetricDisplay"] = resp_agg.apply(
        lambda r: f"{int(r['Responded'])}/{int(r['Total'])} issues ({r['Percentage']:.0f}%)" if r["Responded"] > 0 else "Not ranked yet",
        axis=1,
    )
    r_qualified = resp_agg[resp_agg["Responded"] > 0].sort_values(["Responded", "Percentage"], ascending=[False, False])
    r_unqualified = resp_agg[resp_agg["Responded"] == 0].sort_index()
    r_qualified = r_qualified.reset_index().rename(columns={"index": "NameofResponsibleStaff"})
    r_unqualified = r_unqualified.reset_index().rename(columns={"index": "NameofResponsibleStaff"})
    r_qualified["Rank"] = range(1, len(r_qualified) + 1)
    r_unqualified["Rank"] = None
    responders = pd.concat([r_qualified, r_unqualified], ignore_index=True)

    return solvers, responders
