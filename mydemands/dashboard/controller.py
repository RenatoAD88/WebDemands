from __future__ import annotations

from csv_store import CsvStore
from mydemands.dashboard.layout_persistence_service import LayoutPersistenceService
from mydemands.dashboard.metrics_service import DashboardMetrics, DashboardMetricsService


class MonitoramentoController:
    def __init__(
        self,
        store: CsvStore,
        metrics_service: DashboardMetricsService,
        layout_service: LayoutPersistenceService,
        user_email: str,
    ) -> None:
        self.store = store
        self.metrics_service = metrics_service
        self.layout_service = layout_service
        self.user_email = user_email or "anonimo"

    def load_metrics(self) -> DashboardMetrics:
        rows = self.store.build_view()
        return self.metrics_service.calculate(rows)

    def load_layout_order(self) -> list[str]:
        return self.layout_service.load(self.user_email)

    def save_layout_order(self, order: list[str]) -> None:
        self.layout_service.save(self.user_email, order)
