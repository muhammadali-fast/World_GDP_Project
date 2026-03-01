"""
plugins/inputs.py  —  Input Plugins
=====================================
Two concrete data readers:
  • CSVReader  — reads the wide-format GDP CSV (your main data source)
  • JSONReader — reads GDP data stored as a JSON array of records

Golden Rule: neither class imports TransformationEngine.
Both interact ONLY via the PipelineService Protocol from core/contracts.py.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pandas as pd

from core.contracts import PipelineService   # ← only import from core/

if TYPE_CHECKING:
    pass    # no additional imports needed at runtime


# ─────────────────────────────────────────────────────────────────────────────
class CSVReader:
    """
    Reads a wide-format GDP CSV file and pushes the raw DataFrame
    into the pipeline via the injected PipelineService.

    The CSV is expected to have columns:
        Country Name, Country Code, Indicator Name, Indicator Code,
        <year columns 1960-2024>, Continent
    """

    def __init__(self, filepath: str, service: PipelineService) -> None:
        """
        Args:
            filepath: Path to the CSV data file.
            service:  Any object satisfying PipelineService (the engine).
                      Injected by main.py — this class never creates it.
        """
        self.filepath = filepath
        self.service  = service

    def run(self) -> None:
        """Load the CSV and hand the DataFrame to the service."""
        print(f"\n  [CSVReader] Loading: {self.filepath}")

        try:
            df = pd.read_csv(self.filepath, encoding="utf-8")
            df.columns = df.columns.str.strip()
            print(f"  [CSVReader] Loaded {len(df)} rows, {len(df.columns)} columns")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"[CSVReader] File not found: {self.filepath}\n"
                "Check 'data_source' in config.json"
            )
        except Exception as exc:
            raise RuntimeError(f"[CSVReader] Failed to read CSV: {exc}") from exc

        # Hand off to engine — we don't do any analysis here
        self.service.execute(df)


# ─────────────────────────────────────────────────────────────────────────────
class JSONReader:
    """
    Reads a GDP dataset stored as a JSON file (array of record objects)
    and pushes the DataFrame into the pipeline.

    Expected JSON format — array of objects:
    [
        {
            "Country Name": "Afghanistan",
            "Country Code": "AFG",
            "Indicator Name": "GDP (current US$)",
            "Indicator Code": "NY.GDP.MKTP.CD",
            "Continent": "Asia",
            "1960": null,
            "1961": null,
            ...
            "2023": 17152234637
        },
        ...
    ]
    """

    def __init__(self, filepath: str, service: PipelineService) -> None:
        """
        Args:
            filepath: Path to the JSON data file.
            service:  Any object satisfying PipelineService (the engine).
        """
        self.filepath = filepath
        self.service  = service

    def run(self) -> None:
        """Load the JSON and hand the DataFrame to the service."""
        print(f"\n  [JSONReader] Loading: {self.filepath}")

        try:
            with open(self.filepath, encoding="utf-8") as fh:
                raw = json.load(fh)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"[JSONReader] File not found: {self.filepath}\n"
                "Check 'data_source' in config.json"
            )
        except json.JSONDecodeError as exc:
            raise ValueError(f"[JSONReader] Invalid JSON: {exc}") from exc

        if isinstance(raw, list):
            df = pd.DataFrame(raw)
        elif isinstance(raw, dict) and "data" in raw:
            # Support {"data": [...]} envelope format
            df = pd.DataFrame(raw["data"])
        else:
            raise ValueError(
                "[JSONReader] Unexpected JSON structure. "
                "Expected a list of records or {'data': [...]}"
            )

        df.columns = df.columns.str.strip()
        print(f"  [JSONReader] Loaded {len(df)} rows, {len(df.columns)} columns")

        self.service.execute(df)
