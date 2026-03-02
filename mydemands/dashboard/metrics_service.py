from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Tuple

from csv_store import parse_prazos_list


@dataclass(frozen=True)
class DashboardMetrics:
    total_demandas: int
    concluidas: int
    concluidas_percentual: int
    em_atraso: int
    em_andamento: int
    canceladas: int
    por_status: Dict[str, int]
    por_prioridade: Dict[str, int]
    status_gerais: Dict[str, int]
    big_numbers: Dict[str, int]
    alertas: List[Dict[str, str]]


class DashboardMetricsService:
    """Calcula indicadores com cache simples baseado no fingerprint das demandas."""

    STATUS_ORDER = [
        "Não iniciada",
        "Em andamento",
        "Bloqueado",
        "Requer revisão",
        "Cancelado",
        "Concluído",
    ]

    STATUS_GERAIS_ORDER = [
        "Dentro do prazo",
        "Concluído antes do prazo",
        "Concluído no prazo",
        "Concluída com atraso",
        "Em atraso",
    ]

    def __init__(self) -> None:
        self._last_fingerprint: Tuple[Any, ...] | None = None
        self._last_metrics: DashboardMetrics | None = None

    def calculate(self, rows: Iterable[Dict[str, Any]]) -> DashboardMetrics:
        rows_list = list(rows)
        fingerprint = self._build_fingerprint(rows_list)
        if fingerprint == self._last_fingerprint and self._last_metrics is not None:
            return self._last_metrics

        total = len(rows_list)
        concluidas = 0
        em_andamento = 0
        canceladas = 0
        em_atraso = 0
        por_status: Dict[str, int] = {status: 0 for status in self.STATUS_ORDER}
        por_prioridade: Dict[str, int] = {"Alta": 0, "Média": 0, "Baixa": 0}
        status_gerais: Dict[str, int] = {label: 0 for label in self.STATUS_GERAIS_ORDER}
        alertas: List[Dict[str, str]] = []
        today = date.today()
        tomorrow = today.fromordinal(today.toordinal() + 1)

        for row in rows_list:
            status = str(row.get("Status") or "").strip()
            prioridade = str(row.get("Prioridade") or "").strip()
            projeto = str(row.get("Projeto") or "").strip()
            descricao = str(row.get("Descrição") or "").strip() or "Sem descrição"
            prazo_raw = str(row.get("Prazo") or "")
            timing = str(row.get("Timing") or "").strip().lower()
            demand_id = str(row.get("ID") or "")
            urgente_raw = str(row.get("É Urgente") or row.get("Urgente") or "").strip().lower()
            urgente = urgente_raw in {"sim", "true", "1", "x", "yes"}

            por_status[status] = por_status.get(status, 0) + 1
            if prioridade in por_prioridade:
                por_prioridade[prioridade] += 1

            if status == "Concluído":
                concluidas += 1
            if status == "Em andamento":
                em_andamento += 1
            if status == "Cancelado":
                canceladas += 1

            if "dentro do prazo" in timing:
                status_gerais["Dentro do prazo"] += 1
            elif "concluída antes" in timing:
                status_gerais["Concluído antes do prazo"] += 1
            elif "concluída no prazo" in timing:
                status_gerais["Concluído no prazo"] += 1
            elif "concluída com atraso" in timing:
                status_gerais["Concluída com atraso"] += 1
            elif "em atraso" in timing:
                status_gerais["Em atraso"] += 1

            prazos = parse_prazos_list(prazo_raw)
            if status not in {"Concluído", "Cancelado"} and prazos:
                ordered_prazos = sorted(prazos)
                min_prazo = ordered_prazos[0]
                prazo_display = (
                    min_prazo.strftime("%d/%m/%Y") if len(ordered_prazos) == 1 else f"{len(ordered_prazos)} prazos"
                )
                prazo_tooltip = " | ".join(p.strftime("%d/%m/%Y") for p in ordered_prazos)
                if min_prazo < today:
                    em_atraso += 1
                    alertas.append(
                        {
                            "id": demand_id,
                            "urgente": "Sim" if urgente else "Não",
                            "status": status,
                            "timing": str(row.get("Timing") or "").strip(),
                            "prioridade": prioridade,
                            "prazo": prazo_display,
                            "prazo_tooltip": prazo_tooltip,
                            "prazo_sort": min_prazo.isoformat(),
                            "percentual": str(row.get("% Conclusão") or ""),
                            "data_registro": str(row.get("Data de Registro") or "").strip(),
                            "projeto": projeto,
                            "descricao": descricao,
                            "comentario": str(row.get("Comentário") or "").strip(),
                            "numero_controle": str(row.get("ID Azure") or "").strip(),
                            "responsavel": str(row.get("Responsável") or "").strip(),
                            "reportar": str(row.get("Reportar?") or "").strip(),
                            "nome": str(row.get("Nome") or "").strip(),
                            "time_funcao": str(row.get("Time/Função") or "").strip(),
                            "badge": "Atrasada",
                            "urgente_ordem": 0 if urgente else 1,
                        }
                    )
                elif min_prazo == today:
                    alertas.append(
                        {
                            "id": demand_id,
                            "urgente": "Sim" if urgente else "Não",
                            "status": status,
                            "timing": str(row.get("Timing") or "").strip(),
                            "prioridade": prioridade,
                            "prazo": prazo_display,
                            "prazo_tooltip": prazo_tooltip,
                            "prazo_sort": min_prazo.isoformat(),
                            "percentual": str(row.get("% Conclusão") or ""),
                            "data_registro": str(row.get("Data de Registro") or "").strip(),
                            "projeto": projeto,
                            "descricao": descricao,
                            "comentario": str(row.get("Comentário") or "").strip(),
                            "numero_controle": str(row.get("ID Azure") or "").strip(),
                            "responsavel": str(row.get("Responsável") or "").strip(),
                            "reportar": str(row.get("Reportar?") or "").strip(),
                            "nome": str(row.get("Nome") or "").strip(),
                            "time_funcao": str(row.get("Time/Função") or "").strip(),
                            "badge": "Prazo hoje",
                            "urgente_ordem": 0 if urgente else 1,
                        }
                    )
                elif min_prazo == tomorrow:
                    alertas.append(
                        {
                            "id": demand_id,
                            "urgente": "Sim" if urgente else "Não",
                            "status": status,
                            "timing": str(row.get("Timing") or "").strip(),
                            "prioridade": prioridade,
                            "prazo": prazo_display,
                            "prazo_tooltip": prazo_tooltip,
                            "prazo_sort": min_prazo.isoformat(),
                            "percentual": str(row.get("% Conclusão") or ""),
                            "data_registro": str(row.get("Data de Registro") or "").strip(),
                            "projeto": projeto,
                            "descricao": descricao,
                            "comentario": str(row.get("Comentário") or "").strip(),
                            "numero_controle": str(row.get("ID Azure") or "").strip(),
                            "responsavel": str(row.get("Responsável") or "").strip(),
                            "reportar": str(row.get("Reportar?") or "").strip(),
                            "nome": str(row.get("Nome") or "").strip(),
                            "time_funcao": str(row.get("Time/Função") or "").strip(),
                            "badge": "Vencimento próximo",
                            "urgente_ordem": 0 if urgente else 1,
                        }
                    )

        percentual = int(round((concluidas / total) * 100)) if total else 0
        big_numbers = {
            "Total de Demandas": total,
            "Não iniciado": por_status.get("Não iniciada", 0),
            "Em andamento": por_status.get("Em andamento", 0),
            "Bloqueado": por_status.get("Bloqueado", 0),
            "Requer revisão": por_status.get("Requer revisão", 0),
            "Cancelado": por_status.get("Cancelado", 0),
            "Concluído": por_status.get("Concluído", 0),
        }

        metrics = DashboardMetrics(
            total_demandas=total,
            concluidas=concluidas,
            concluidas_percentual=percentual,
            em_atraso=em_atraso,
            em_andamento=em_andamento,
            canceladas=canceladas,
            por_status=por_status,
            por_prioridade=por_prioridade,
            status_gerais=status_gerais,
            big_numbers=big_numbers,
            alertas=sorted(
                alertas,
                key=lambda x: (
                    x.get("urgente_ordem", 1),
                    {"Atrasada": 0, "Prazo hoje": 1, "Vencimento próximo": 2}.get(x["badge"], 3),
                    x.get("prazo_sort", ""),
                    x["id"],
                ),
            ),
        )
        self._last_fingerprint = fingerprint
        self._last_metrics = metrics
        return metrics

    def _build_fingerprint(self, rows: List[Dict[str, Any]]) -> Tuple[Any, ...]:
        ordered = []
        for row in rows:
            ordered.append(
                (
                    str(row.get("_id") or ""),
                    str(row.get("ID") or ""),
                    str(row.get("Status") or ""),
                    str(row.get("Prioridade") or ""),
                    str(row.get("Prazo") or ""),
                    str(row.get("Projeto") or ""),
                    str(row.get("Descrição") or ""),
                    str(row.get("Timing") or ""),
                    str(row.get("% Conclusão") or ""),
                )
            )
        ordered.sort()
        return tuple(ordered)
