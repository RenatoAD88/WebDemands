from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class DemandColumnSchema:
    id: str
    label: str
    type: str = "text"
    default_visible: bool = True
    default_width: int = 140
    group: str = "demands"
    order_default: int = 0


class DemandasSchemaRegistry:
    SCHEMA_VERSION = 2

    def __init__(self) -> None:
        self._columns: List[DemandColumnSchema] = [
            DemandColumnSchema("id", "ID", default_width=90, order_default=0),
            DemandColumnSchema("urgente", "É Urgente", default_width=90, order_default=1),
            DemandColumnSchema("status", "Status", default_width=120, order_default=2),
            DemandColumnSchema("timing", "Timing", default_width=120, order_default=3),
            DemandColumnSchema("prioridade", "Prioridade", default_width=120, order_default=4),
            DemandColumnSchema("data_registro", "Data de Registro", default_width=120, order_default=5),
            DemandColumnSchema("prazo", "Prazo", default_width=120, order_default=6),
            DemandColumnSchema("projeto", "Projeto", default_width=140, order_default=7),
            DemandColumnSchema("descricao", "Descrição", default_width=220, order_default=8),
            DemandColumnSchema("comentario", "Comentário", default_width=220, order_default=9),
            DemandColumnSchema("numero_controle", "Num Controle", default_width=120, order_default=10),
            DemandColumnSchema("percentual", "% Conclusão", default_width=100, order_default=11),
            DemandColumnSchema("responsavel", "Responsável", default_width=130, order_default=12),
            DemandColumnSchema("reportar", "Reportar?", default_width=90, order_default=13),
            DemandColumnSchema("nome", "Nome", default_width=140, order_default=14),
            DemandColumnSchema("time_funcao", "Time/Função", default_width=140, order_default=15),
        ]

    def demand_columns(self) -> List[DemandColumnSchema]:
        return list(self._columns)

    def default_table_preferences(self, visible_ids: List[str] | None = None) -> Dict:
        visible_ids = visible_ids or [c.id for c in self._columns if c.default_visible]
        return {
            "columns": [
                {
                    "id": c.id,
                    "visible": c.id in visible_ids,
                    "order": idx,
                    "width": c.default_width,
                }
                for idx, c in enumerate(self._columns)
            ],
            "sort": {"id": "prazo", "direction": "asc"},
            "layout": {"density": "comfortable"},
        }

    def by_id(self) -> Dict[str, DemandColumnSchema]:
        return {c.id: c for c in self._columns}
