from __future__ import annotations

from typing import Dict, List


def required_fields(payload: Dict[str, str], prazo_count: int) -> List[str]:
    missing: List[str] = []
    if not (payload.get("Descrição") or "").strip():
        missing.append("Descrição")
    if not (payload.get("Prioridade") or "").strip():
        missing.append("Prioridade")
    if not (payload.get("Status") or "").strip():
        missing.append("Status")
    if not (payload.get("Responsável") or "").strip():
        missing.append("Responsável")
    if not (payload.get("Projeto") or "").strip():
        missing.append("Projeto")
    if prazo_count == 0:
        missing.append("Prazo")

    status = (payload.get("Status") or "").strip()
    perc = (payload.get("% Conclusão") or "").strip()
    concl = (payload.get("Data Conclusão") or "").strip()
    if (status == "Concluído" or perc in ("1", "100%", "100% - Concluído")) and not concl:
        missing.append("Data Conclusão")

    return missing
