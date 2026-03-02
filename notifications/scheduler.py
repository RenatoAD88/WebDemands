from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Protocol, List

from PySide6.QtCore import QObject, QTimer

from csv_store import parse_prazos_list
from .models import Notification, NotificationType


class TimeProvider(Protocol):
    def now(self) -> datetime: ...


class SystemTimeProvider:
    def now(self) -> datetime:
        return datetime.now()


class DemandasRepository(Protocol):
    def list_open_demands(self) -> Iterable[dict]: ...


@dataclass
class DeadlineEvent:
    demand_id: str
    notification_type: NotificationType


class DeadlineScheduler(QObject):
    def __init__(self, repo: DemandasRepository, emitter, time_provider: TimeProvider | None = None):
        super().__init__()
        self.repo = repo
        self.emitter = emitter
        self.time_provider = time_provider or SystemTimeProvider()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_now)

    def start(self, interval_minutes: int) -> None:
        self.timer.start(max(1, interval_minutes) * 60_000)

    def update_interval(self, interval_minutes: int) -> None:
        self.start(interval_minutes)

    def check_now(self) -> List[DeadlineEvent]:
        now = self.time_provider.now()
        today = now.date()
        events: List[DeadlineEvent] = []

        for demand in self.repo.list_open_demands():
            demand_id = str(demand.get("ID") or demand.get("_id") or "")
            demand_description = str(demand.get("Descrição") or "").strip()
            deadline_text = demand.get("Prazo") or ""
            deadlines = parse_prazos_list(deadline_text)
            if not deadlines:
                continue
            closest = min(deadlines)
            delta = closest - today
            if delta < timedelta(days=0):
                evt = Notification(
                    type=NotificationType.PRAZO_ESTOURADO,
                    title=f"Demanda #{demand_id} atrasada",
                    body=f"Prazo em {closest.strftime('%d/%m/%Y')}.",
                    payload={
                        "demand_id": demand_id,
                        "demand_description": demand_description,
                        "route": "atrasadas",
                        "deadline_date": closest.isoformat(),
                        "event_code": "deadline_overdue",
                    },
                    demand_id=demand_id,
                    demand_description=demand_description,
                )
                self.emitter(evt)
                events.append(DeadlineEvent(demand_id, NotificationType.PRAZO_ESTOURADO))
            elif delta <= timedelta(days=1):
                evt = Notification(
                    type=NotificationType.PRAZO_PROXIMO,
                    title=f"Prazo hoje: #{demand_id}",
                    body=f"Demanda vence em {closest.strftime('%d/%m/%Y')}.",
                    payload={
                        "demand_id": demand_id,
                        "demand_description": demand_description,
                        "route": "demanda",
                        "deadline_date": closest.isoformat(),
                        "event_code": "deadline_due",
                    },
                    demand_id=demand_id,
                    demand_description=demand_description,
                )
                self.emitter(evt)
                events.append(DeadlineEvent(demand_id, NotificationType.PRAZO_PROXIMO))
        return events
