"""Consistent, accessible Plotly chart construction."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .schema import ConfidenceResult, ExecutionResult, QueryPlan

NAVY = "#102A43"
GREEN = "#14805E"
BLUE = "#2F6BFF"
ORANGE = "#E8871E"
LIGHT_GREEN = "#DFF4EC"
GRAY = "#6B7C93"
PALETTE = [GREEN, BLUE, ORANGE, "#7A5AF8", "#00A6A6", "#D64550"]


def _base_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left", "font": {"size": 20, "color": NAVY}},
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Inter, Arial, sans-serif", "color": NAVY},
        margin={"l": 40, "r": 30, "t": 70, "b": 50},
        legend_title_text="",
        hoverlabel={"bgcolor": "white", "font_size": 13},
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#D9E2EC")
    fig.update_yaxes(gridcolor="#E8EEF4", zeroline=False, rangemode="tozero")
    return fig


def build_result_chart(result: ExecutionResult, plan: QueryPlan) -> go.Figure | None:
    table = result.table
    if result.status != "supported" or table.empty or plan.chart_type == "table":
        return None

    if plan.intent in {"top_n", "skill_frequency"}:
        x = table.columns[0]
        y = "Postings"
        plot = table.sort_values(y, ascending=True)
        fig = px.bar(plot, x=y, y=x, orientation="h", text=y, color_discrete_sequence=[GREEN])
        fig.update_traces(textposition="outside", cliponaxis=False)
        return _base_layout(fig, "Verified ranking from the supplied data")

    if plan.intent in {"median", "average", "comparison"}:
        if len(table.columns) >= 2 and any("midpoint" in str(column).casefold() for column in table.columns):
            group = table.columns[0]
            value = next(column for column in table.columns if "midpoint" in str(column).casefold())
            plot = table.sort_values(value, ascending=True)
            fig = px.bar(plot, x=value, y=group, orientation="h", text=value, color_discrete_sequence=[BLUE])
            fig.update_traces(texttemplate="$%{x:,.0f}", textposition="outside", cliponaxis=False)
            fig.update_xaxes(tickprefix="$", tickformat=",")
            return _base_layout(fig, "Salary midpoint with minimum sample-size rules")

    if plan.intent == "percentage":
        fig = px.pie(table, names=table.columns[0], values="Postings", hole=0.62, color_discrete_sequence=[ORANGE, GREEN])
        fig.update_traces(textposition="inside", textinfo="percent+label")
        return _base_layout(fig, "Salary disclosure coverage")

    if plan.intent == "trend":
        fig = px.line(table, x="Period", y="Postings", markers=True, color_discrete_sequence=[GREEN])
        fig.update_traces(line={"width": 4}, marker={"size": 8})
        return _base_layout(fig, "Posting volume over time")

    if plan.intent == "missing_data":
        plot = table.sort_values("Missing", ascending=True)
        fig = px.bar(plot, x="Missing", y="Field", orientation="h", color_discrete_sequence=[ORANGE])
        return _base_layout(fig, "Missing values by field")

    return None


def build_quality_gauge(score: int) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"color": NAVY, "size": 40}},
            title={"text": "Dataset quality", "font": {"color": NAVY, "size": 18}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": GRAY},
                "bar": {"color": GREEN},
                "bgcolor": "white",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 60], "color": "#FDE8E8"},
                    {"range": [60, 80], "color": "#FFF2D8"},
                    {"range": [80, 100], "color": LIGHT_GREEN},
                ],
            },
        )
    )
    fig.update_layout(height=280, margin={"l": 30, "r": 30, "t": 50, "b": 20}, paper_bgcolor="white")
    return fig


def build_confidence_gauge(confidence: ConfidenceResult) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=confidence.score,
            number={"suffix": "/100", "font": {"color": NAVY, "size": 34}},
            title={"text": confidence.label, "font": {"color": NAVY, "size": 17}},
            gauge={
                "axis": {"range": [0, 100], "visible": False},
                "bar": {"color": GREEN if confidence.score >= 64 else ORANGE},
                "bgcolor": "#EEF3F7",
                "borderwidth": 0,
            },
        )
    )
    fig.update_layout(height=220, margin={"l": 20, "r": 20, "t": 45, "b": 10}, paper_bgcolor="white")
    return fig


def build_missingness_chart(missingness: pd.DataFrame) -> go.Figure:
    plot = missingness.head(15).sort_values("Percent", ascending=True)
    fig = px.bar(plot, x="Percent", y="Field", orientation="h", color_discrete_sequence=[ORANGE])
    fig.update_xaxes(ticksuffix="%")
    return _base_layout(fig, "Most incomplete fields")


def build_dashboard_charts(frame: pd.DataFrame) -> dict[str, go.Figure]:
    charts: dict[str, go.Figure] = {}

    roles = frame.groupby("normalized_role").size().reset_index(name="Postings").sort_values("Postings", ascending=False).head(10)
    role_fig = px.bar(roles.sort_values("Postings"), x="Postings", y="normalized_role", orientation="h", color_discrete_sequence=[GREEN])
    charts["roles"] = _base_layout(role_fig, "Most common role categories")

    modes = frame.groupby("work_mode").size().reset_index(name="Postings")
    mode_fig = px.pie(modes, names="work_mode", values="Postings", hole=0.58, color_discrete_sequence=PALETTE)
    mode_fig.update_traces(textinfo="percent+label")
    charts["work_mode"] = _base_layout(mode_fig, "Work-mode mix")

    skill_rows: list[dict[str, str]] = []
    for value in frame["required_skills"].fillna(""):
        for skill in {item.strip() for item in str(value).split("|") if item.strip()}:
            skill_rows.append({"Skill": skill})
    skills = pd.DataFrame(skill_rows).groupby("Skill").size().reset_index(name="Postings").sort_values("Postings", ascending=False).head(12)
    skill_fig = px.bar(skills.sort_values("Postings"), x="Postings", y="Skill", orientation="h", color_discrete_sequence=[BLUE])
    charts["skills"] = _base_layout(skill_fig, "Top required skills")

    salary = frame[frame["salary_midpoint"].notna()].groupby("experience_level").agg(
        **{"Median midpoint": ("salary_midpoint", "median"), "Sample size": ("salary_midpoint", "size")}
    ).reset_index()
    order = ["Internship", "Entry Level", "Associate", "Mid Level", "Senior", "Unknown"]
    salary["order"] = salary["experience_level"].map({value: index for index, value in enumerate(order)}).fillna(99)
    salary = salary.sort_values("order")
    salary_fig = px.bar(salary, x="experience_level", y="Median midpoint", text="Sample size", color_discrete_sequence=[ORANGE])
    salary_fig.update_yaxes(tickprefix="$", tickformat=",")
    charts["salary"] = _base_layout(salary_fig, "Median salary midpoint by experience")

    dated = frame[frame["date_posted"].notna()].copy()
    dated["Period"] = dated["date_posted"].dt.to_period("M").astype(str)
    trend = dated.groupby("Period").size().reset_index(name="Postings")
    trend_fig = px.line(trend, x="Period", y="Postings", markers=True, color_discrete_sequence=[GREEN])
    trend_fig.update_traces(line={"width": 4}, marker={"size": 8})
    charts["trend"] = _base_layout(trend_fig, "Posting volume by month")
    return charts


def build_career_match_chart(signals: pd.DataFrame) -> go.Figure | None:
    if signals.empty:
        return None
    plot = signals.sort_values("Postings", ascending=True)
    color_map = {"Matched": GREEN, "Opportunity": ORANGE}
    fig = px.bar(plot, x="Postings", y="Skill", orientation="h", color="Status", color_discrete_map=color_map)
    return _base_layout(fig, "Your skills against the strongest role signals")


def build_scenario_chart(frame: pd.DataFrame) -> go.Figure:
    plot = frame.copy()
    fig = go.Figure()
    fig.add_bar(name="Postings", x=plot["Selection"], y=plot["Postings"], marker_color=GREEN)
    fig.add_scatter(
        name="Median salary midpoint",
        x=plot["Selection"],
        y=plot["Median salary midpoint"],
        mode="lines+markers+text",
        text=[f"${value:,.0f}" if pd.notna(value) else "N/A" for value in plot["Median salary midpoint"]],
        textposition="top center",
        marker={"color": BLUE, "size": 10},
        line={"color": BLUE, "width": 3},
        yaxis="y2",
    )
    fig.update_layout(
        yaxis={"title": "Postings", "rangemode": "tozero", "gridcolor": "#E8EEF4"},
        yaxis2={"title": "Median salary midpoint", "overlaying": "y", "side": "right", "tickprefix": "$", "tickformat": ","},
        barmode="group",
    )
    return _base_layout(fig, "Scenario comparison")
