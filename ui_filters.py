from __future__ import annotations

from typing import Any, Dict, List, Optional

from csv_store import parse_prazos_list


def _normalize_status(status: str) -> str:
    value = (status or "").strip().casefold()
    aliases = {
        "não iniciado": "não iniciada",
        "não iniciada": "não iniciada",
        "em andamento": "em andamento",
        "bloqueado": "bloqueado",
        "em espera": "bloqueado",
        "requer revisão": "requer revisão",
        "requer revisao": "requer revisão",
        "concluído": "concluído",
        "concluido": "concluído",
        "cancelado": "cancelado",
    }
    return aliases.get(value, value)


def filter_rows(
    rows: List[Dict[str, Any]],
    text_query: str = "",
    status: str = "",
    status_values: Optional[List[str]] = None,
    prioridade: str = "",
    responsavel: str = "",
    prazo: str = "",
    projeto: str = "",
) -> List[Dict[str, Any]]:
    q = (text_query or "").strip().lower()
    st = (status or "").strip()
    selected_statuses = {
        _normalize_status(value)
        for value in (status_values or [])
        if (value or "").strip()
    }
    if st and not selected_statuses:
        selected_statuses = {_normalize_status(st)}
    pr = (prioridade or "").strip()
    rs = (responsavel or "").strip().lower()
    prazo_str = (prazo or "").strip()
    projeto_filtro = (projeto or "").strip()

    out: List[Dict[str, Any]] = []
    for row in rows:
        row_status = _normalize_status(row.get("Status") or "")
        if selected_statuses and row_status not in selected_statuses:
            continue
        if pr and (row.get("Prioridade") or "").strip() != pr:
            continue
        if rs and rs not in (row.get("Responsável") or "").strip().lower():
            continue
        if projeto_filtro and (row.get("Projeto") or "").strip() != projeto_filtro:
            continue
        if prazo_str:
            prazos = parse_prazos_list((row.get("Prazo") or "").replace("*", ""))
            if prazo_str not in {p.strftime("%d/%m/%Y") for p in prazos}:
                continue
        if q:
            hay = " ".join([
                str(row.get("Projeto", "") or ""),
                str(row.get("Descrição", "") or ""),
                str(row.get("Comentário", "") or row.get("Comentario", "") or ""),
                str(row.get("ID Azure", "") or ""),
                str(row.get("Responsável", "") or ""),
                str(row.get("Nome", "") or ""),
                str(row.get("Time/Função", "") or ""),
            ]).lower()
            if q not in hay:
                continue
        out.append(row)
    return out


def summary_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    pending = 0
    delayed = 0
    concluded = 0
    for row in rows:
        status = (row.get("Status") or "").strip()
        timing = (row.get("Timing") or "").strip().lower()
        if status == "Concluído":
            concluded += 1
        elif status != "Cancelado":
            pending += 1
        if "atras" in timing:
            delayed += 1
    inside_deadline = max(pending - delayed, 0)
    return {
        "pending": pending,
        "inside_deadline": inside_deadline,
        "delayed": delayed,
        "concluded": concluded,
    }
