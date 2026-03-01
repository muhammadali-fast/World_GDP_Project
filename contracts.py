"""
core/contracts.py  —  The Contracts (Protocols)
================================================
The Core OWNS these definitions.
All plugins must satisfy these shapes — but this file
never imports from plugins/.

Two Protocols:
  • DataSink        — any output plugin must implement write()
  • PipelineService — any input plugin calls execute() on this
"""

from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class DataSink(Protocol):
    """
    Outbound abstraction.
    The Core calls sink.write(results) without knowing whether
    the output goes to the console, charts, a file, or anything else.
    Any class with a matching write() signature satisfies this Protocol.
    """

    def write(self, results: dict) -> None:
        """
        Receive the final analysis results dict and render them.

        Args:
            results: dict with keys like 'top_10', 'bottom_10', etc.
                     Each value is a pandas DataFrame or a scalar.
        """
        ...


@runtime_checkable
class PipelineService(Protocol):
    """
    Inbound abstraction.
    Input plugins call service.execute(raw_data) to push data
    into the Core.  They never know they are talking to
    TransformationEngine — only to this Protocol.
    """

    def execute(self, raw_data: Any) -> None:
        """
        Accept raw data from an input plugin and run the full pipeline.

        Args:
            raw_data: a pandas DataFrame loaded by the input plugin.
        """
        ...
