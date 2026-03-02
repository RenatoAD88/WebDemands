from __future__ import annotations

import json
import os
import re
import uuid
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

TEAM_CONTROL_FILE = "team_control.json"
MAX_SECTIONS = 10
MAX_MEMBERS_PER_SECTION = 20


def build_team_control_report_rows(sections: List[TeamSection], year: int, month: int) -> List[List[str]]:
    total_days = month_days(year, month)
    month_participation_header = "Participação\nMês"
    rows: List[List[str]] = [
        ["Ano", str(year), "Mês", f"{month:02d}"],
        ["Use", "P - Presente", "A - Ausente", "K - Com demanda", "F - Férias", "D - Day-off", "H - Feriado", "R - Recesso"],
    ]

    for section in sections:
        rows.append([])
        rows.append([section.name])
        headers = ["Nome"] + [f"{d:02d}/{month:02d}" for d in range(1, total_days + 1)] + [month_participation_header]
        rows.append(headers)

        for member in section.members:
            row = [member.name]
            for d in range(1, total_days + 1):
                row.append(member.entries.get(date(year, month, d).isoformat(), ""))
            row.append(str(monthly_k_count(member, year, month)))
            rows.append(row)

        footer = ["Participação"]
        for d in range(1, total_days + 1):
            curr = date(year, month, d)
            total = participation_for_date([member.entries.get(curr.isoformat(), "") for member in section.members])
            footer.append(str(total) if total > 0 else "")
        footer.append("")
        rows.append(footer)

    return rows

WEEKDAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
STATUS_COLORS: Dict[str, tuple[int, int, int, int, int, int]] = {
    "F": (128, 90, 213, 255, 255, 255),
    "A": (239, 68, 68, 255, 255, 255),
    "P": (37, 99, 235, 255, 255, 255),
    "D": (147, 197, 253, 15, 23, 42),
    "R": (253, 224, 71, 15, 23, 42),
    "H": (250, 204, 21, 15, 23, 42),
    "K": (74, 222, 128, 15, 23, 42),
}


@dataclass
class TeamMember:
    id: str
    name: str
    entries: Dict[str, str]


@dataclass
class TeamSection:
    id: str
    name: str
    members: List[TeamMember]


class TeamControlStore:
    def __init__(self, base_dir: str):
        self.path = os.path.join(base_dir, TEAM_CONTROL_FILE)
        self.sections: List[TeamSection] = []
        self._period_sections: Dict[str, List[TeamSection]] = {}
        self._active_period = self._period_key(date.today().year, date.today().month)
        self.load()

    def _period_key(self, year: int, month: int) -> str:
        return f"{int(year):04d}-{int(month):02d}"

    def set_period(self, year: int, month: int) -> None:
        self._active_period = self._period_key(year, month)
        self.sections = self._period_sections.get(self._active_period, [])

    def get_sections_for_period(self, year: int, month: int) -> List[TeamSection]:
        key = self._period_key(year, month)
        return self._period_sections.get(key, [])

    def load(self) -> None:
        if not os.path.exists(self.path):
            self.sections = []
            return
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        periods_raw = raw.get("periods")
        if isinstance(periods_raw, dict):
            self._period_sections = {
                str(period): self._parse_sections(data.get("sections", []))
                for period, data in periods_raw.items()
                if isinstance(data, dict)
            }
        else:
            # Compatibilidade com formato legado.
            legacy_sections = self._parse_sections(raw.get("sections", []))
            self._period_sections = {}
            if legacy_sections:
                self._period_sections[self._active_period] = legacy_sections

        self.sections = self._period_sections.get(self._active_period, [])

    def _parse_sections(self, raw_sections: List[dict]) -> List[TeamSection]:
        out: List[TeamSection] = []
        for s in raw_sections:
            members: List[TeamMember] = []
            for m in s.get("members", []):
                members.append(
                    TeamMember(
                        id=str(m.get("id") or uuid.uuid4().hex),
                        name=str(m.get("name") or "").strip(),
                        entries={str(k): str(v) for k, v in (m.get("entries") or {}).items()},
                    )
                )
            out.append(
                TeamSection(
                    id=str(s.get("id") or uuid.uuid4().hex),
                    name=str(s.get("name") or "").strip(),
                    members=members,
                )
            )
        return out

    def save(self) -> None:
        self._period_sections[self._active_period] = self.sections
        payload = self.to_payload()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def to_payload(self) -> Dict[str, Dict[str, Dict[str, List[dict]]]]:
        payload = {"periods": {}}
        for period, sections in self._period_sections.items():
            payload["periods"][period] = {
                "sections": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "members": [
                            {
                                "id": m.id,
                                "name": m.name,
                                "entries": m.entries,
                            }
                            for m in s.members
                        ],
                    }
                    for s in sections
                ]
            }
        return payload

    def create_section(self, name: str) -> TeamSection:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Nome do time é obrigatório.")
        if len(self.sections) >= MAX_SECTIONS:
            raise ValueError("Limite de 10 times atingido.")
        section = TeamSection(id=uuid.uuid4().hex, name=cleaned, members=[])
        self.sections.append(section)
        self.save()
        return section

    def delete_section(self, section_id: str) -> None:
        self.sections = [s for s in self.sections if s.id != section_id]
        self.save()

    def add_member(self, section_id: str, name: str) -> TeamMember:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Nome do funcionário é obrigatório.")
        section = self._get_section(section_id)
        if len(section.members) >= MAX_MEMBERS_PER_SECTION:
            raise ValueError("Limite de 20 funcionários por time atingido.")
        member = TeamMember(id=uuid.uuid4().hex, name=cleaned, entries={})
        section.members.append(member)
        self.save()
        return member

    def copy_members_to_section(self, target_year: int, target_month: int, target_section_id: str, names: List[str]) -> int:
        cleaned_names = [n.strip() for n in names if (n or "").strip()]
        if not cleaned_names:
            return 0

        original_period = self._active_period
        added = 0
        try:
            self.set_period(target_year, target_month)
            section = self._get_section(target_section_id)

            if len(section.members) + len(cleaned_names) > MAX_MEMBERS_PER_SECTION:
                raise ValueError("Limite de 20 funcionários por time atingido.")

            for name in cleaned_names:
                member = TeamMember(id=uuid.uuid4().hex, name=name, entries={})
                section.members.append(member)
                added += 1

            self.save()
            return added
        finally:
            self._active_period = original_period
            self.sections = self._period_sections.get(original_period, [])

    def remove_member(self, section_id: str, member_id: str) -> None:
        section = self._get_section(section_id)
        section.members = [m for m in section.members if m.id != member_id]
        self.save()

    def rename_member(self, section_id: str, member_id: str, name: str) -> None:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Nome do funcionário é obrigatório.")
        member = self._get_member(section_id, member_id)
        member.name = cleaned
        self.save()

    def set_entry(self, section_id: str, member_id: str, when: date, code: str) -> None:
        member = self._get_member(section_id, member_id)
        key = when.isoformat()
        value = (code or "").strip().upper()
        if not value:
            member.entries.pop(key, None)
        else:
            member.entries[key] = value
        self.save()

    def _get_section(self, section_id: str) -> TeamSection:
        for s in self.sections:
            if s.id == section_id:
                return s
        raise ValueError("Time não encontrado.")

    def _get_member(self, section_id: str, member_id: str) -> TeamMember:
        section = self._get_section(section_id)
        for m in section.members:
            if m.id == member_id:
                return m
        raise ValueError("Funcionário não encontrado.")


def month_days(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def participation_for_date(entries: List[str]) -> int:
    return sum(1 for e in entries if (e or "").strip().upper() in {"K", "P"})


def monthly_k_count(member: TeamMember, year: int, month: int) -> int:
    total_days = month_days(year, month)
    count = 0
    for d in range(1, total_days + 1):
        key = date(year, month, d).isoformat()
        if (member.entries.get(key) or "").strip().upper() in {"K", "P"}:
            count += 1
    return count


def split_member_names(raw_names: str) -> List[str]:
    return [piece.strip() for piece in re.split(r"[,\n]+", raw_names or "") if piece.strip()]
