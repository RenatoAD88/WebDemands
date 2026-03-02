from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .models import Channel, NotificationType, Preferences
from .store import NotificationStore


class NotificationSettingsDialog(QDialog):
    def __init__(self, store: NotificationStore, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Configurações de Notificações")

        self.pref = self.store.load_preferences()
        self.type_boxes = {}
        self.channel_boxes = {}

        form = QFormLayout()
        for nt in NotificationType:
            box = QCheckBox("Ativar")
            box.setChecked(self.pref.enabled_types.get(nt, True))
            self.type_boxes[nt] = box
            form.addRow(nt.value, box)

        for ch in Channel:
            box = QCheckBox("Ativar")
            box.setChecked(self.pref.enabled_channels.get(ch, False))
            self.channel_boxes[ch] = box
            form.addRow(f"Canal {ch.value}", box)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(self.pref.scheduler_interval_minutes)
        form.addRow("Intervalo do scheduler (min)", self.interval_spin)

        save_btn = QPushButton("Salvar")
        cancel_btn = QPushButton("Cancelar")
        save_btn.clicked.connect(self._save)
        cancel_btn.clicked.connect(self.reject)
        actions = QHBoxLayout()
        actions.addWidget(save_btn)
        actions.addWidget(cancel_btn)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addLayout(actions)

    def _save(self) -> None:
        pref = Preferences()
        pref.enabled_types = {nt: box.isChecked() for nt, box in self.type_boxes.items()}
        pref.enabled_channels = {ch: box.isChecked() for ch, box in self.channel_boxes.items()}
        pref.scheduler_interval_minutes = self.interval_spin.value()
        pref.muted_until_epoch = self.pref.muted_until_epoch
        self.store.save_preferences(pref)
        self.accept()
