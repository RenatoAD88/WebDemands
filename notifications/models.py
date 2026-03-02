from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _load_brasilia_tz() -> ZoneInfo | timezone:
    try:
        return ZoneInfo("America/Sao_Paulo")
    except ZoneInfoNotFoundError:
        # Fallback for packaged environments where IANA tz database is absent.
        return timezone(timedelta(hours=-3), name="America/Sao_Paulo")


BRASILIA_TZ = _load_brasilia_tz()


def brasilia_now() -> datetime:
    return datetime.now(BRASILIA_TZ)


class NotificationType(str, Enum):
    NOVA_DEMANDA = "NOVA_DEMANDA"
    ALTERACAO_STATUS = "ALTERACAO_STATUS"
    PRAZO_PROXIMO = "PRAZO_PROXIMO"
    PRAZO_ESTOURADO = "PRAZO_ESTOURADO"
    MENSAGEM_GERAL_ERRO = "MENSAGEM_GERAL_ERRO"


class Channel(str, Enum):
    SYSTEM = "SYSTEM"
    IN_APP = "IN_APP"
    SOUND = "SOUND"


@dataclass
class Notification:
    type: NotificationType
    title: str
    body: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=brasilia_now)
    read: bool = False
    id: int | None = None
    demand_id: str | None = None
    demand_description: str | None = None

    def __post_init__(self) -> None:
        payload = self.payload or {}
        payload_demand_id = payload.get("demand_id")
        payload_description = payload.get("demand_description")

        if self.demand_id is None and payload_demand_id not in (None, ""):
            self.demand_id = str(payload_demand_id)
        elif self.demand_id:
            payload["demand_id"] = str(self.demand_id)

        if self.demand_description is None and payload_description not in (None, ""):
            self.demand_description = str(payload_description)
        elif self.demand_description:
            payload["demand_description"] = str(self.demand_description)

        self.payload = payload


@dataclass
class Preferences:
    enabled_types: Dict[NotificationType, bool] = field(
        default_factory=lambda: {nt: True for nt in NotificationType}
    )
    enabled_channels: Dict[Channel, bool] = field(
        default_factory=lambda: {
            Channel.SYSTEM: True,
            Channel.IN_APP: True,
            Channel.SOUND: False,
        }
    )
    scheduler_interval_minutes: int = 15
    muted_until_epoch: float = 0.0

    def type_enabled(self, notification_type: NotificationType) -> bool:
        return bool(self.enabled_types.get(notification_type, True))

    def channel_enabled(self, channel: Channel) -> bool:
        return bool(self.enabled_channels.get(channel, False))

    def is_muted(self, now_epoch: float) -> bool:
        return self.muted_until_epoch > now_epoch
