"""
The heart of the application.

Responsibilities:
  1. Clean & reshape the raw wide-format GDP data into long format
  2. Run all 8 required analyses
  3. Push the results to whatever DataSink was injected at startup

Golden Rule: this file NEVER imports from plugins/.
It only knows about the DataSink Protocol from core/contracts.py.
"""

from __future__ import annotations
from typing import Any
import pandas as pd
from core.contracts import DataSink


class TransformationEngine:
    """
    The Core Domain Engine.

    Created by main.py with a DataSink and config injected in — it never
    creates its own sink and never reads files itself.

     """

    def __init__(self, sink: DataSink, config: dict) -> None:
        """
        Args:
            sink:   Any object satisfying the DataSink Protocol.
                    Injected at runtime — could be ConsoleWriter or GraphicsChartWriter.
            config: The parsed config.json dictionary.
        """
        self.sink   = sink
        self.config = config

    def execute(self, raw_data: Any) -> None:
        """
        Called by the input plugin after loading data.
        Cleans → Analyses → Writes.
        """
        print("\n" + "=" * 60)
        print("  GDP ANALYSIS ENGINE — STARTING PIPELINE")
        print("=" * 60)

        df = self._clean(raw_data)
        print(f" ---Data cleaned--- ")

        results = self._run_all_analyses(df)
        print(f"\n***** All 8 analyses complete — sending to output sink... *****")

        self.sink.write(results)

        print("\n" + "=" * 60)
        print("  GDP ANALYSIS ENGINE — PIPELINE COMPLETE")
        print("=" * 60 + "\n")

    # ── Step 1: Clean & reshape ────────────────────────────────────────────────
    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert wide-format CSV (one column per year) → long format.
        Result columns: Country Name, Country Code, Continent, Year, Value
        """
        df = df.copy()
        df.columns = df.columns.str.strip()

        id_cols  = ["Country Name", "Country Code", "Indicator Name",
                    "Indicator Code", "Continent"]
        year_cols = [c for c in df.columns if c.isdigit()]

        df_long = df.melt(
            id_vars    = id_cols,
            value_vars = year_cols,
            var_name   = "Year",
            value_name = "Value",
        )

        df_long["Year"]  = df_long["Year"].astype(int)
        df_long["Value"] = pd.to_numeric(df_long["Value"], errors="coerce")

        df_long = df_long.dropna(subset=["Value"])
        df_long = df_long[df_long["Value"] > 0]

        for col in ["Country Name", "Country Code", "Continent"]:
            df_long[col] = df_long[col].str.strip()

        return df_long.reset_index(drop=True)

    # ── Step 2: Run all 8 analyses ────────────────────────────────────────────
    def _run_all_analyses(self, df: pd.DataFrame) -> dict:
        """
        Run every required analysis and collect results in one dict.
        Keys match what the output plugins expect.
        """
        continent    = self.config.get("continent", "Asia")
        year_range   = self.config.get("year_range", [2000, 2020])
        top_n_year   = self.config.get("top_n_year", 2015)
        decline_years= self.config.get("decline_years", 5)

        start_year, end_year = int(year_range[0]), int(year_range[1])

        print(f"\n  Config  →  continent={continent}  |  "
              f"years={start_year}–{end_year}  |  "
              f"top_n_year={top_n_year}  |  decline_years={decline_years}")

        results = {
            "config": {
                "continent":     continent,
                "start_year":    start_year,
                "end_year":      end_year,
                "top_n_year":    top_n_year,
                "decline_years": decline_years,
            },
            "top_10":         self._top_10(df, continent, top_n_year),
            "bottom_10":      self._bottom_10(df, continent, top_n_year),
            "growth_rate":    self._growth_rate(df, continent, start_year, end_year),
            "avg_continent":  self._avg_by_continent(df, start_year, end_year),
            "global_trend":   self._global_gdp_trend(df, start_year, end_year),
            "fastest":        self._fastest_growing_continent(df, start_year, end_year),
            "decline":        self._consistent_decline(df, decline_years),
            "contribution":   self._continent_contribution(df, start_year, end_year),
        }
        return results

    # Analysis 1 — Top 10 Countries by GDP
    def _top_10(self, df: pd.DataFrame, continent: str, year: int) -> pd.DataFrame:
        """Top 10 countries by GDP for a given continent and year."""
        mask = (df["Continent"] == continent) & (df["Year"] == year)
        filtered = df[mask]

        if filtered.empty:
            print(f"  ⚠ No data for continent='{continent}' year={year} (top 10)")
            return pd.DataFrame(columns=["Country Name", "GDP (USD)"])

        result = (
            filtered
            .groupby("Country Name", as_index=False)["Value"]
            .sum()
            .rename(columns={"Value": "GDP (USD)"})
            .nlargest(10, "GDP (USD)")
            .reset_index(drop=True)
        )
        result.index = result.index + 1          # rank starts at 1
        return result

    # Analysis 2 — Bottom 10 Countries by GDP
    def _bottom_10(self, df: pd.DataFrame, continent: str, year: int) -> pd.DataFrame:
        """Bottom 10 countries by GDP for a given continent and year."""
        mask = (df["Continent"] == continent) & (df["Year"] == year)
        filtered = df[mask]

        if filtered.empty:
            print(f"  No data for continent='{continent}' year={year} (bottom 10)")
            return pd.DataFrame(columns=["Country Name", "GDP (USD)"])

        result = (
            filtered
            .groupby("Country Name", as_index=False)["Value"]
            .sum()
            .rename(columns={"Value": "GDP (USD)"})
            .nsmallest(10, "GDP (USD)")
            .reset_index(drop=True)
        )
        result.index = result.index + 1
        return result

    # Analysis 3 — GDP Growth Rate per Country
    def _growth_rate(
        self, df: pd.DataFrame, continent: str,
        start_year: int, end_year: int
    ) -> pd.DataFrame:
        """
        Year-over-year GDP growth rate (%) for each country
        in the given continent over the year range.
        Returns columns: Country Name, Year, Value, Growth_Rate (%)
        """
        mask = (
            (df["Continent"] == continent) &
            (df["Year"] >= start_year) &
            (df["Year"] <= end_year)
        )
        filtered = df[mask].copy()

        if filtered.empty:
            return pd.DataFrame(columns=["Country Name", "Year", "Value", "Growth_Rate (%)"])

        filtered = filtered.sort_values(["Country Name", "Year"])

        filtered["Growth_Rate (%)"] = (
            filtered
            .groupby("Country Name")["Value"]
            .pct_change()
            .mul(100)
            .round(2)
        )

        return (
            filtered[["Country Name", "Year", "Value", "Growth_Rate (%)"]]
            .dropna(subset=["Growth_Rate (%)"])
            .reset_index(drop=True)
        )

    # Analysis 4 — Average GDP by Continent
    def _avg_by_continent(
        self, df: pd.DataFrame, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """Average GDP per continent over the given year range."""
        mask = (df["Year"] >= start_year) & (df["Year"] <= end_year)
        filtered = df[mask]

        result = (
            filtered
            .groupby("Continent", as_index=False)["Value"]
            .mean()
            .rename(columns={"Value": "Average GDP (USD)"})
            .sort_values("Average GDP (USD)", ascending=False)
            .reset_index(drop=True)
        )
        result["Average GDP (USD)"] = result["Average GDP (USD)"].round(2)
        return result

    # Analysis 5 — Total Global GDP Trend
    def _global_gdp_trend(
        self, df: pd.DataFrame, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """
        Total world GDP per year over the given range.
        Only uses rows where Continent != 'Global' to avoid double-counting.
        """
        mask = (
            (df["Year"] >= start_year) &
            (df["Year"] <= end_year) &
            (df["Continent"] != "Global")
        )
        filtered = df[mask]

        result = (
            filtered
            .groupby("Year", as_index=False)["Value"]
            .sum()
            .rename(columns={"Value": "Total GDP (USD)"})
            .sort_values("Year")
            .reset_index(drop=True)
        )
        return result

    # Analysis 6 — Fastest Growing Continent
    def _fastest_growing_continent(
        self, df: pd.DataFrame, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """
        Compares total GDP of each continent at start vs end year
        and returns them ranked by growth rate (%).
        """
        mask_start = (df["Year"] == start_year) & (df["Continent"] != "Global")
        mask_end   = (df["Year"] == end_year)   & (df["Continent"] != "Global")

        gdp_start = (
            df[mask_start]
            .groupby("Continent")["Value"].sum()
            .rename("GDP_Start")
        )
        gdp_end = (
            df[mask_end]
            .groupby("Continent")["Value"].sum()
            .rename("GDP_End")
        )

        combined = pd.concat([gdp_start, gdp_end], axis=1).dropna()

        if combined.empty:
            return pd.DataFrame(columns=["Continent", "Growth Rate (%)", "Winner"])

        combined["Growth Rate (%)"] = (
            ((combined["GDP_End"] - combined["GDP_Start"]) / combined["GDP_Start"])
            .mul(100)
            .round(2)
        )

        result = (
            combined
            .reset_index()
            .rename(columns={"index": "Continent"})
            [["Continent", "GDP_Start", "GDP_End", "Growth Rate (%)"]]
            .sort_values("Growth Rate (%)", ascending=False)
            .reset_index(drop=True)
        )

        result["GDP_Start"] = result["GDP_Start"].round(2)
        result["GDP_End"]   = result["GDP_End"].round(2)

        # Mark the winner
        result["Winner"] = ""
        if not result.empty:
            result.loc[0, "Winner"] = "*** FASTEST ***"

        return result

    # Analysis 7 — Countries with Consistent GDP Decline
    def _consistent_decline(
        self, df: pd.DataFrame, decline_years: int
    ) -> pd.DataFrame:
        """
        Find countries where GDP declined every single year
        for the last `decline_years` consecutive years in the dataset.
        """
        data = df[df["Continent"] != "Global"].copy()
        data = data.sort_values(["Country Name", "Year"])

        def has_consistent_decline(group: pd.Series) -> bool:
            """Return True if the last N year-over-year changes are all negative."""
            diffs = group.diff().dropna()
            if len(diffs) < decline_years:
                return False
            return bool((diffs.tail(decline_years) < 0).all())

        declining = (
            data.groupby("Country Name")["Value"]
            .apply(has_consistent_decline)
        )

        declining_countries = declining[declining].index.tolist()

        if not declining_countries:
            return pd.DataFrame(columns=["Country Name", "Continent", "Years of Decline"])

        last_years = (
            data[data["Country Name"].isin(declining_countries)]
            .sort_values("Year")
            .groupby("Country Name")
            .last()
            .reset_index()
            [["Country Name", "Continent", "Year", "Value"]]
            .rename(columns={"Year": "Last Year", "Value": "Last GDP (USD)"})
        )
        last_years["Years of Decline"] = decline_years
        last_years["Last GDP (USD)"]   = last_years["Last GDP (USD)"].round(2)

        return last_years.reset_index(drop=True)

    # Analysis 8 — Continent Contribution to Global GDP
    def _continent_contribution(
        self, df: pd.DataFrame, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """
        Each continent's share (%) of total global GDP
        summed over the given year range.
        """
        mask = (
            (df["Year"] >= start_year) &
            (df["Year"] <= end_year) &
            (df["Continent"] != "Global")
        )
        filtered = df[mask]

        continent_totals = (
            filtered
            .groupby("Continent")["Value"]
            .sum()
        )

        global_total = continent_totals.sum()

        result = (
            continent_totals
            .reset_index()
            .rename(columns={"Value": "Total GDP (USD)"})
        )
        result["Contribution (%)"] = (
            (result["Total GDP (USD)"] / global_total * 100).round(2)
        )
        result = result.sort_values("Contribution (%)", ascending=False).reset_index(drop=True)
        result["Total GDP (USD)"] = result["Total GDP (USD)"].round(2)

        return result