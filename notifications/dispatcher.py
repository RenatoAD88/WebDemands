from __future__ import annotations

import logging
import time
from typing import Callable

from .models import Channel, Notification
from .store import NotificationStore

LOGGER = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(
        self,
        store: NotificationStore,
        system_notifier,
        inapp_notifier,
        is_app_focused: Callable[[], bool],
        play_sound: Callable[[], None] | None = None,
    ):
        self.store = store
        self.system_notifier = system_notifier
        self.inapp_notifier = inapp_notifier
        self.is_app_focused = is_app_focused
        self.play_sound = play_sound

    def dispatch(self, notification: Notification) -> int | None:
        pref = self.store.load_preferences()
        if not pref.type_enabled(notification.type):
            LOGGER.info("Notificação desabilitada por tipo: %s", notification.type)
            return None

        if not self.store.should_dispatch(notification):
            LOGGER.info("Ocorrência já notificada anteriormente: %s", notification.type)
            return None

        notification_id = self.store.insert(notification)

        if pref.is_muted(time.time()):
            return notification_id

        if self.is_app_focused() and pref.channel_enabled(Channel.IN_APP):
            self.inapp_notifier.notify(notification.title, notification.body)
        elif pref.channel_enabled(Channel.SYSTEM):
            self.system_notifier.notify(notification.title, notification.body)

        if pref.channel_enabled(Channel.SOUND) and self.play_sound:
            self.play_sound()
        return notification_id
