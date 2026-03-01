"""
main.py  —  The Orchestrator (Bootstrap Layer)
===============================================
This is the ONLY file that knows about everything.
Its single responsibility is:
    1. Read config.json
    2. Instantiate the Output Sink
    3. Instantiate the Core Engine  → inject the Sink
    4. Instantiate the Input Reader → inject the Engine
    5. Call reader.run()  — data flows automatically

Zero analysis logic lives here.
Zero chart logic lives here.
Adding a new input or output format = add one line to a dict below.
"""

import json
import sys
from pathlib import Path

# ── Input drivers ─────────────────────────────────────────────────────────────
from plugins.inputs import CSVReader, JSONReader

# ── Output drivers ────────────────────────────────────────────────────────────
from plugins.outputs import ConsoleWriter, GraphicsChartWriter

# ── Core engine ───────────────────────────────────────────────────────────────
from core.engine import TransformationEngine


# ── Registry / Factory maps ───────────────────────────────────────────────────
# To add a new input format: just add a key → class entry here.
# Zero other files need to change.
INPUT_DRIVERS: dict = {
    "csv":  CSVReader,
    "json": JSONReader,
}

# To swap outputs (console vs charts): change "output" in config.json.
OUTPUT_DRIVERS: dict = {
    "console":  ConsoleWriter,
    "graphics": GraphicsChartWriter,
}


# ── Bootstrap ─────────────────────────────────────────────────────────────────
def bootstrap(config_path: str = "config.json") -> None:
    """
    Wire all components together and start the pipeline.

    Dependency Injection order (always this sequence):
        Sink  →  Engine(sink)  →  Reader(engine)  →  reader.run()
    """
    print("\n" + "=" * 60)
    print("  GDP ANALYSIS SYSTEM — PHASE 2")
    print("  Modular Architecture  |  Dependency Inversion")
    print("=" * 60)

    # ── 1. Load configuration ─────────────────────────────────────────────────
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"\n  ERROR: config.json not found at '{config_path}'")
        sys.exit(1)

    with open(config_file, encoding="utf-8") as fh:
        config = json.load(fh)

    # Remove comment key if present
    config.pop("_comment", None)

    print(f"\n  Config loaded:")
    print(f"    Input  driver : {config.get('input')}")
    print(f"    Output driver : {config.get('output')}")
    print(f"    Data source   : {config.get('data_source')}")
    print(f"    Continent     : {config.get('continent')}")
    print(f"    Year range    : {config.get('year_range')}")
    print(f"    Top-N year    : {config.get('top_n_year')}")
    print(f"    Decline years : {config.get('decline_years')}")

    # ── 2. Validate driver keys ───────────────────────────────────────────────
    input_key  = config.get("input",  "csv")
    output_key = config.get("output", "console")

    if input_key not in INPUT_DRIVERS:
        print(f"\n  ERROR: Unknown input driver '{input_key}'.")
        print(f"  Valid options: {list(INPUT_DRIVERS.keys())}")
        sys.exit(1)

    if output_key not in OUTPUT_DRIVERS:
        print(f"\n  ERROR: Unknown output driver '{output_key}'.")
        print(f"  Valid options: {list(OUTPUT_DRIVERS.keys())}")
        sys.exit(1)

    # ── 3. Instantiate Sink (Output) ──────────────────────────────────────────
    SinkClass = OUTPUT_DRIVERS[output_key]
    if output_key == "graphics":
        sink = SinkClass(output_dir="output")
    else:
        sink = SinkClass()

    print(f"\n  ✔ Sink ready     : {SinkClass.__name__}")

    # ── 4. Instantiate Engine — inject Sink ───────────────────────────────────
    engine = TransformationEngine(sink=sink, config=config)
    print(f"  ✔ Engine ready   : {TransformationEngine.__name__}")

    # ── 5. Instantiate Reader — inject Engine ─────────────────────────────────
    ReaderClass = INPUT_DRIVERS[input_key]
    reader = ReaderClass(
        filepath = config.get("data_source", "data/gdp_data.csv"),
        service  = engine,
    )
    print(f"  ✔ Reader ready   : {ReaderClass.__name__}")

    # ── 6. Run — data flows through the pipeline ──────────────────────────────
    print(f"\n  Starting pipeline...")
    reader.run()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        bootstrap()
    except FileNotFoundError as exc:
        print(f"\n  FILE ERROR: {exc}")
        sys.exit(1)
    except ValueError as exc:
        print(f"\n  CONFIG ERROR: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        import traceback
        print(f"\n  UNEXPECTED ERROR: {exc}")
        traceback.print_exc()
        sys.exit(1)
