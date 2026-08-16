"""Disable Chroma product telemetry for the local-first application."""

from chromadb.telemetry.product import ProductTelemetryClient, ProductTelemetryEvent
from overrides import override


class NoOpTelemetry(ProductTelemetryClient):
    """Chroma telemetry adapter that never sends or stores events."""

    @override
    def capture(self, event: ProductTelemetryEvent) -> None:
        return None
