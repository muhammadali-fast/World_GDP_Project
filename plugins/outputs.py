"""
plugins/outputs.py  —  Output Plugins
=======================================
Two concrete output sinks:
  • ConsoleWriter        — prints all 8 analyses as formatted tables to terminal
  • GraphicsChartWriter  — saves 8 matplotlib charts as PNG files

Golden Rule: neither class imports anything from core/engine.py.
Both satisfy the DataSink Protocol purely by having write(results: dict).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")          # non-interactive backend — safe for all environments
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
#  Shared formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_usd(value: float) -> str:
    """Format a number as a compact USD string (T / B / M)."""
    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"${value/1e12:.2f}T"
    if abs_v >= 1e9:
        return f"${value/1e9:.2f}B"
    if abs_v >= 1e6:
        return f"${value/1e6:.2f}M"
    return f"${value:,.0f}"


def _section(title: str, width: int = 65) -> str:
    bar = "═" * width
    return f"\n{bar}\n  {title}\n{bar}"


# ─────────────────────────────────────────────────────────────────────────────
class ConsoleWriter:
    """
    Prints all 8 analyses as clean, readable tables to the terminal.
    Satisfies DataSink Protocol via write(results: dict).
    """

    def write(self, results: dict) -> None:
        cfg = results.get("config", {})
        print(_section(
            f"GDP ANALYSIS RESULTS  |  "
            f"{cfg.get('continent','?')}  |  "
            f"{cfg.get('start_year','?')}–{cfg.get('end_year','?')}"
        ))

        self._print_top_10(results["top_10"],    cfg)
        self._print_bottom_10(results["bottom_10"],  cfg)
        self._print_growth_rate(results["growth_rate"], cfg)
        self._print_avg_continent(results["avg_continent"], cfg)
        self._print_global_trend(results["global_trend"],  cfg)
        self._print_fastest(results["fastest"],       cfg)
        self._print_decline(results["decline"],       cfg)
        self._print_contribution(results["contribution"], cfg)

        print(_section("ALL ANALYSES COMPLETE"))

    # ── individual printers ───────────────────────────────────────────────────

    def _print_top_10(self, df: pd.DataFrame, cfg: dict) -> None:
        print(_section(
            f"1. TOP 10 COUNTRIES BY GDP"
            f"  [{cfg.get('continent')}  |  {cfg.get('top_n_year')}]"
        ))
        if df.empty:
            print("  No data available.")
            return
        for rank, row in df.iterrows():
            print(f"  {rank:>2}. {row['Country Name']:<35} {_fmt_usd(row['GDP (USD)'])}")

    def _print_bottom_10(self, df: pd.DataFrame, cfg: dict) -> None:
        print(_section(
            f"2. BOTTOM 10 COUNTRIES BY GDP"
            f"  [{cfg.get('continent')}  |  {cfg.get('top_n_year')}]"
        ))
        if df.empty:
            print("  No data available.")
            return
        for rank, row in df.iterrows():
            print(f"  {rank:>2}. {row['Country Name']:<35} {_fmt_usd(row['GDP (USD)'])}")

    def _print_growth_rate(self, df: pd.DataFrame, cfg: dict) -> None:
        print(_section(
            f"3. GDP GROWTH RATE PER COUNTRY"
            f"  [{cfg.get('continent')}  |  "
            f"{cfg.get('start_year')}–{cfg.get('end_year')}]"
        ))
        if df.empty:
            print("  No data available.")
            return
        # Show last recorded growth rate per country
        latest = (
            df.sort_values("Year")
            .groupby("Country Name")
            .last()
            .reset_index()
            .sort_values("Growth_Rate (%)", ascending=False)
        )
        print(f"  {'Country':<35} {'Last Year':>9} {'Growth Rate':>13}")
        print(f"  {'-'*35} {'-'*9} {'-'*13}")
        for _, row in latest.iterrows():
            sign = "▲" if row["Growth_Rate (%)"] >= 0 else "▼"
            print(f"  {row['Country Name']:<35} "
                  f"{int(row['Year']):>9}  "
                  f"{sign}{abs(row['Growth_Rate (%)']):>10.2f}%")

    def _print_avg_continent(self, df: pd.DataFrame, cfg: dict) -> None:
        print(_section(
            f"4. AVERAGE GDP BY CONTINENT"
            f"  [{cfg.get('start_year')}–{cfg.get('end_year')}]"
        ))
        if df.empty:
            print("  No data available.")
            return
        for _, row in df.iterrows():
            print(f"  {row['Continent']:<20} {_fmt_usd(row['Average GDP (USD)'])}")

    def _print_global_trend(self, df: pd.DataFrame, cfg: dict) -> None:
        print(_section(
            f"5. TOTAL GLOBAL GDP TREND"
            f"  [{cfg.get('start_year')}–{cfg.get('end_year')}]"
        ))
        if df.empty:
            print("  No data available.")
            return
        for _, row in df.iterrows():
            bar_len = int(row["Total GDP (USD)"] / df["Total GDP (USD)"].max() * 30)
            bar     = "█" * bar_len
            print(f"  {int(row['Year'])}: {_fmt_usd(row['Total GDP (USD)']):>12}  {bar}")

    def _print_fastest(self, df: pd.DataFrame, cfg: dict) -> None:
        print(_section(
            f"6. FASTEST GROWING CONTINENT"
            f"  [{cfg.get('start_year')}–{cfg.get('end_year')}]"
        ))
        if df.empty:
            print("  No data available.")
            return
        print(f"  {'Continent':<20} {'Growth Rate':>12}  ")
        print(f"  {'-'*20} {'-'*12}")
        for _, row in df.iterrows():
            winner = f"  ← {row['Winner']}" if row['Winner'] else ""
            print(f"  {row['Continent']:<20} {row['Growth Rate (%)']:>11.2f}%{winner}")

    def _print_decline(self, df: pd.DataFrame, cfg: dict) -> None:
        print(_section(
            f"7. COUNTRIES WITH CONSISTENT GDP DECLINE"
            f"  [last {cfg.get('decline_years')} years]"
        ))
        if df.empty:
            print(f"  No countries found with {cfg.get('decline_years')} consecutive years of decline.")
            return
        for _, row in df.iterrows():
            print(f"  {row['Country Name']:<35} "
                  f"{row['Continent']:<15} "
                  f"Last GDP: {_fmt_usd(row['Last GDP (USD)'])}")

    def _print_contribution(self, df: pd.DataFrame, cfg: dict) -> None:
        print(_section(
            f"8. CONTINENT CONTRIBUTION TO GLOBAL GDP"
            f"  [{cfg.get('start_year')}–{cfg.get('end_year')}]"
        ))
        if df.empty:
            print("  No data available.")
            return
        for _, row in df.iterrows():
            bar_len = int(row["Contribution (%)"] / 100 * 40)
            bar     = "█" * bar_len
            print(f"  {row['Continent']:<20} {row['Contribution (%)']:>5.2f}%  {bar}")


# ─────────────────────────────────────────────────────────────────────────────
class GraphicsChartWriter:
    """
    Saves 8 matplotlib charts as PNG files to an output directory.
    Satisfies DataSink Protocol via write(results: dict).
    """

    # Shared style constants
    PALETTE = [
        "#4C9BE8", "#50FA7B", "#FFB86C", "#FF79C6",
        "#BD93F9", "#8BE9FD", "#FF5555", "#F1FA8C",
        "#6272A4", "#44475A",
    ]
    BG      = "#1E1E2E"
    FG      = "#F8F8F2"
    GRID    = "#44475A"

    def __init__(self, output_dir: str = "output") -> None:
        self.output_dir = Path(output_dir)

    def write(self, results: dict) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        cfg = results.get("config", {})

        print(f"\n  [GraphicsChartWriter] Saving charts → {self.output_dir}/")

        saved = []
        saved += [self._chart_top_10(results["top_10"],       cfg)]
        saved += [self._chart_bottom_10(results["bottom_10"],    cfg)]
        saved += [self._chart_growth_rate(results["growth_rate"],  cfg)]
        saved += [self._chart_avg_continent(results["avg_continent"], cfg)]
        saved += [self._chart_global_trend(results["global_trend"],  cfg)]
        saved += [self._chart_fastest(results["fastest"],       cfg)]
        saved += [self._chart_decline(results["decline"],       cfg)]
        saved += [self._chart_contribution(results["contribution"], cfg)]

        plt.close("all")

        for path in saved:
            if path:
                print(f"  ✔ {path.name}")

        print(f"\n  [GraphicsChartWriter] {len([p for p in saved if p])} charts saved.")

    # ── Shared style helpers ──────────────────────────────────────────────────

    def _new_fig(self, title: str, figsize: tuple = (11, 6)) -> tuple:
        """Create a styled figure and axes."""
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(self.BG)
        ax.set_facecolor(self.BG)
        ax.set_title(title, color=self.FG, fontsize=13, fontweight="bold", pad=14)
        ax.tick_params(colors=self.FG, labelsize=9)
        ax.xaxis.label.set_color(self.FG)
        ax.yaxis.label.set_color(self.FG)
        for spine in ax.spines.values():
            spine.set_edgecolor(self.GRID)
        ax.grid(axis="y", color=self.GRID, linestyle="--", alpha=0.4)
        return fig, ax

    def _save(self, fig: Any, filename: str) -> Path:
        path = self.output_dir / filename
        fig.savefig(path, dpi=150, bbox_inches="tight",
                    facecolor=self.BG, edgecolor="none")
        plt.close(fig)
        return path

    def _add_usd_labels(self, ax: Any, bars: Any) -> None:
        """Add compact USD labels above each bar."""
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2, h * 1.01,
                _fmt_usd(h), ha="center", va="bottom",
                color=self.FG, fontsize=7.5, fontweight="bold"
            )

    # ── Chart 1 — Top 10 ─────────────────────────────────────────────────────
    def _chart_top_10(self, df: pd.DataFrame, cfg: dict) -> Path | None:
        if df.empty:
            return None
        fig, ax = self._new_fig(
            f"Top 10 Countries by GDP  |  {cfg.get('continent')}  |  {cfg.get('top_n_year')}"
        )
        colors = self.PALETTE[:len(df)]
        bars   = ax.bar(df["Country Name"], df["GDP (USD)"], color=colors, edgecolor="#282A36")
        self._add_usd_labels(ax, bars)
        ax.set_xlabel("Country", labelpad=8)
        ax.set_ylabel("GDP (USD)", labelpad=8)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: _fmt_usd(x)))
        plt.xticks(rotation=35, ha="right", color=self.FG)
        plt.tight_layout()
        return self._save(fig, "01_top_10_countries.png")

    # ── Chart 2 — Bottom 10 ──────────────────────────────────────────────────
    def _chart_bottom_10(self, df: pd.DataFrame, cfg: dict) -> Path | None:
        if df.empty:
            return None
        fig, ax = self._new_fig(
            f"Bottom 10 Countries by GDP  |  {cfg.get('continent')}  |  {cfg.get('top_n_year')}"
        )
        colors = self.PALETTE[2:2+len(df)]
        bars   = ax.bar(df["Country Name"], df["GDP (USD)"], color=colors, edgecolor="#282A36")
        self._add_usd_labels(ax, bars)
        ax.set_xlabel("Country", labelpad=8)
        ax.set_ylabel("GDP (USD)", labelpad=8)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: _fmt_usd(x)))
        plt.xticks(rotation=35, ha="right", color=self.FG)
        plt.tight_layout()
        return self._save(fig, "02_bottom_10_countries.png")

    # ── Chart 3 — Growth Rate (top 15 by absolute growth) ────────────────────
    def _chart_growth_rate(self, df: pd.DataFrame, cfg: dict) -> Path | None:
        if df.empty:
            return None
        # Show last recorded growth rate per country, top 15 by absolute value
        latest = (
            df.sort_values("Year")
            .groupby("Country Name")
            .last()
            .reset_index()
            .sort_values("Growth_Rate (%)", ascending=False)
            .head(15)
        )
        fig, ax = self._new_fig(
            f"GDP Growth Rate (Last Recorded)  |  "
            f"{cfg.get('continent')}  |  "
            f"{cfg.get('start_year')}–{cfg.get('end_year')}",
            figsize=(12, 6)
        )
        bar_colors = [
            self.PALETTE[0] if v >= 0 else self.PALETTE[6]
            for v in latest["Growth_Rate (%)"]
        ]
        bars = ax.bar(latest["Country Name"], latest["Growth_Rate (%)"],
                      color=bar_colors, edgecolor="#282A36")
        ax.axhline(0, color=self.FG, linewidth=0.8, linestyle="--")
        ax.set_xlabel("Country", labelpad=8)
        ax.set_ylabel("Growth Rate (%)", labelpad=8)
        plt.xticks(rotation=40, ha="right", color=self.FG)
        plt.tight_layout()
        return self._save(fig, "03_gdp_growth_rate.png")

    # ── Chart 4 — Average GDP by Continent (horizontal bar) ──────────────────
    def _chart_avg_continent(self, df: pd.DataFrame, cfg: dict) -> Path | None:
        if df.empty:
            return None
        fig, ax = self._new_fig(
            f"Average GDP by Continent  |  "
            f"{cfg.get('start_year')}–{cfg.get('end_year')}",
            figsize=(10, 5)
        )
        colors = self.PALETTE[:len(df)]
        bars   = ax.barh(df["Continent"], df["Average GDP (USD)"],
                         color=colors, edgecolor="#282A36")
        ax.set_xlabel("Average GDP (USD)", labelpad=8)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: _fmt_usd(x)))
        # Value labels
        for bar in bars:
            w = bar.get_width()
            ax.text(w * 1.01, bar.get_y() + bar.get_height() / 2,
                    _fmt_usd(w), va="center", ha="left",
                    color=self.FG, fontsize=8, fontweight="bold")
        plt.tight_layout()
        return self._save(fig, "04_avg_gdp_by_continent.png")

    # ── Chart 5 — Global GDP Trend (line) ────────────────────────────────────
    def _chart_global_trend(self, df: pd.DataFrame, cfg: dict) -> Path | None:
        if df.empty:
            return None
        fig, ax = self._new_fig(
            f"Total Global GDP Trend  |  "
            f"{cfg.get('start_year')}–{cfg.get('end_year')}",
            figsize=(12, 5)
        )
        ax.plot(df["Year"], df["Total GDP (USD)"],
                color=self.PALETTE[0], linewidth=2.5, marker="o",
                markersize=5, markerfacecolor=self.PALETTE[1])
        ax.fill_between(df["Year"], df["Total GDP (USD)"],
                        alpha=0.15, color=self.PALETTE[0])
        ax.set_xlabel("Year", labelpad=8)
        ax.set_ylabel("Total GDP (USD)", labelpad=8)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: _fmt_usd(x)))
        plt.xticks(rotation=30, ha="right", color=self.FG)
        plt.tight_layout()
        return self._save(fig, "05_global_gdp_trend.png")

    # ── Chart 6 — Fastest Growing Continent ──────────────────────────────────
    def _chart_fastest(self, df: pd.DataFrame, cfg: dict) -> Path | None:
        if df.empty:
            return None
        fig, ax = self._new_fig(
            f"Continent GDP Growth  |  "
            f"{cfg.get('start_year')} → {cfg.get('end_year')}",
            figsize=(9, 5)
        )
        bar_colors = [
            self.PALETTE[1] if v >= 0 else self.PALETTE[6]
            for v in df["Growth Rate (%)"]
        ]
        bars = ax.bar(df["Continent"], df["Growth Rate (%)"],
                      color=bar_colors, edgecolor="#282A36")
        ax.axhline(0, color=self.FG, linewidth=0.8, linestyle="--")
        ax.set_ylabel("Growth Rate (%)", labelpad=8)
        # Annotate the winner
        if not df.empty and df.iloc[0]["Winner"]:
            ax.annotate(
                "*** FASTEST ***",
                xy=(df.iloc[0]["Continent"], df.iloc[0]["Growth Rate (%)"]),
                xytext=(0, 14), textcoords="offset points",
                ha="center", color=self.PALETTE[3], fontsize=10, fontweight="bold"
            )
        plt.xticks(rotation=25, ha="right", color=self.FG)
        plt.tight_layout()
        return self._save(fig, "06_fastest_growing_continent.png")

    # ── Chart 7 — Consistent Decline ─────────────────────────────────────────
    def _chart_decline(self, df: pd.DataFrame, cfg: dict) -> Path | None:
        if df.empty:
            # Create an informational "no data" chart
            fig, ax = self._new_fig(
                f"Countries with Consistent GDP Decline  |  "
                f"Last {cfg.get('decline_years')} Years"
            )
            ax.text(0.5, 0.5,
                    f"No countries found with\n"
                    f"{cfg.get('decline_years')} consecutive years of decline",
                    transform=ax.transAxes, ha="center", va="center",
                    color=self.PALETTE[1], fontsize=14, fontweight="bold")
            ax.axis("off")
            return self._save(fig, "07_consistent_decline.png")

        fig, ax = self._new_fig(
            f"Countries with Consistent GDP Decline  |  "
            f"Last {cfg.get('decline_years')} Years",
            figsize=(11, max(4, len(df) * 0.6 + 2))
        )
        bars = ax.barh(
            df["Country Name"], df["Last GDP (USD)"],
            color=self.PALETTE[6], edgecolor="#282A36"
        )
        ax.set_xlabel("Last Recorded GDP (USD)", labelpad=8)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: _fmt_usd(x)))
        for bar in bars:
            w = bar.get_width()
            ax.text(w * 1.01, bar.get_y() + bar.get_height() / 2,
                    _fmt_usd(w), va="center", ha="left",
                    color=self.FG, fontsize=8)
        plt.tight_layout()
        return self._save(fig, "07_consistent_decline.png")

    # ── Chart 8 — Continent Contribution (pie) ───────────────────────────────
    def _chart_contribution(self, df: pd.DataFrame, cfg: dict) -> Path | None:
        if df.empty:
            return None
        fig, ax = plt.subplots(figsize=(9, 7))
        fig.patch.set_facecolor(self.BG)
        ax.set_facecolor(self.BG)

        wedges, texts, autotexts = ax.pie(
            df["Contribution (%)"],
            labels      = df["Continent"],
            autopct     = lambda pct: f"{pct:.1f}%" if pct > 2 else "",
            colors      = self.PALETTE[:len(df)],
            startangle  = 90,
            wedgeprops  = {"edgecolor": self.BG, "linewidth": 2},
            textprops   = {"color": self.FG, "fontsize": 10},
        )
        for autotext in autotexts:
            autotext.set_color(self.BG)
            autotext.set_fontweight("bold")
            autotext.set_fontsize(8)

        ax.set_title(
            f"Continent Contribution to Global GDP  |  "
            f"{cfg.get('start_year')}–{cfg.get('end_year')}",
            color=self.FG, fontsize=13, fontweight="bold", pad=14
        )
        plt.tight_layout()
        return self._save(fig, "08_continent_contribution.png")
