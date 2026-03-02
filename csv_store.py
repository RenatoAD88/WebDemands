from __future__ import annotations

import csv
import base64
import hashlib
import hmac
import io
import json
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Dict, Any

from validation import validate_payload, normalize_prazo_text, ValidationError

CSV_NAME = "data.csv"
DELIMITER = ";"
EXPORT_TEMPLATE_VERSION = "1"
EXPORT_VERSION_PREFIX = "# MYDEMANDS_EXPORT_TEMPLATE_VERSION="
ENC_MAGIC = b"MYDEMANDS_ENC_V1"
KEY_FILE_NAME = ".demandas.key"

DISPLAY_COLUMNS = [
    "ID",
    "É Urgente?",
    "Status",
    "Timing",
    "Prioridade",
    "Data de Registro",
    "Prazo",
    "Data Conclusão",
    "Projeto",
    "Descrição",
    "Comentário",
    "ID Azure",
    "% Conclusão",
    "Responsável",
    "Reportar?",
    "Nome",
    "Time/Função",
    "eisenhower_column",
]

CSV_COLUMNS = [
    "_id",
    "ID",
    "É Urgente?",
    "Status",
    "Prioridade",
    "Data de Registro",
    "Prazo",
    "Data Conclusão",
    "Projeto",
    "Descrição",
    "Comentário",
    "ID Azure",
    "% Conclusão",
    "Responsável",
    "Reportar?",
    "Nome",
    "Time/Função",
    "eisenhower_column",
]

LEGACY_TO_NEW = {
    "Urgente": "É Urgente?",
    "Data Entrada": "Data de Registro",
    "Data Entrega": "Data Conclusão",
}


def _map_legacy_keys(payload: Dict[str, str]) -> Dict[str, str]:
    if not payload:
        return payload
    p = dict(payload)
    for old, new in LEGACY_TO_NEW.items():
        if old in p and new not in p:
            p[new] = p.get(old, "")
    return p


def parse_ddmmyyyy(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        return None


def parse_prazos_list(prazo_text: str) -> List[date]:
    prazo_text = normalize_prazo_text(prazo_text or "")
    if not prazo_text:
        return []
    out: List[date] = []
    for p in [x.strip() for x in prazo_text.split(",") if x.strip()]:
        d = parse_ddmmyyyy(p)
        if d:
            out.append(d)
    return sorted(set(out))


def priority_rank(p: str) -> int:
    p = (p or "").strip().lower()
    if p == "alta":
        return 0
    if p in ("média", "media"):
        return 1
    if p == "baixa":
        return 2
    return 9


def percent_is_100(stored: str) -> bool:
    v = (stored or "").strip()
    if not v:
        return False
    try:
        f = float(v.replace(",", ".").replace("%", ""))
    except Exception:
        return False
    if f > 1.0 and f <= 100:
        f = f / 100.0
    return abs(f - 1.0) < 1e-9


def calc_timing(status: str, prazos: List[date], conclusao: Optional[date], today: date) -> str:
    st = (status or "").strip().lower()

    if st == "cancelado":
        return "Cancelado"

    if not prazos:
        return "Sem Prazo Definido"

    # Em aberto
    if st not in ("concluído", "concluido", "cancelado"):
        # regra: se alguma data do prazo é hoje, é Dentro do Prazo
        if today in prazos:
            return "Dentro do Prazo"
        if min(prazos) < today and conclusao is None:
            return "Em Atraso"
        return "Dentro do Prazo"

    # Concluído
    if conclusao is None:
        return "Concluído"

    p = min(prazos)
    if conclusao > p:
        return "Concluída com Atraso"
    if conclusao == p:
        return "Concluída no Prazo"
    return "Concluída antes do Prazo"


def percent_display(stored: str) -> str:
    v = (stored or "").strip()
    if not v:
        return ""
    try:
        f = float(v.replace(",", ".").replace("%", ""))
    except Exception:
        return ""
    if f > 1.0 and f <= 100:
        f = f / 100.0
    steps = [0.0, 0.25, 0.5, 0.75, 1.0]
    closest = min(steps, key=lambda s: abs(s - f))
    return f"{int(round(closest * 100))}%"


def prazo_display(raw_prazo: str) -> str:
    p = normalize_prazo_text(raw_prazo or "")
    if not p:
        return ""
    parts = [x.strip() for x in p.split(",") if x.strip()]
    if len(parts) <= 1:
        return parts[0] if parts else ""
    return "\n".join(
        f"{x}*{',' if i < len(parts) - 1 else ''}"
        for i, x in enumerate(parts)
    )


def _require_conclusao_date_if_needed(status: str, perc: str, concl: str):
    """
    Regras novas (integridade):
    - Se status == Concluído => Data Conclusão obrigatória
    - Se % == 1 => Data Conclusão obrigatória
    """
    st = (status or "").strip()
    concl = (concl or "").strip()
    if st == "Concluído" and not concl:
        raise ValidationError("Para Status = Concluído, o campo Data Conclusão é obrigatório.")
    if percent_is_100(perc or "") and not concl:
        raise ValidationError("Para % Conclusão = 100%, o campo Data Conclusão é obrigatório.")


def _autofix_consistency(payload: Dict[str, str]) -> Dict[str, str]:
    """
    Automação de consistência:
    - Se Data Conclusão preenchida => Status = Concluído e % = 1
    - Se Status = Concluído => % = 1
    - Se % = 1 => Status = Concluído
    """
    p = dict(payload)

    concl = (p.get("Data Conclusão") or "").strip()
    status = (p.get("Status") or "").strip()
    perc = (p.get("% Conclusão") or "").strip()

    if status == "Cancelado":
        p["Data Conclusão"] = ""
        p["% Conclusão"] = "0"
        return p

    if concl:
        p["Status"] = "Concluído"
        p["% Conclusão"] = "1"
        return p

    if status == "Concluído":
        p["% Conclusão"] = "1"

    if percent_is_100(perc):
        p["Status"] = "Concluído"
        p["% Conclusão"] = "1"

    return p


@dataclass
class DemandRow:
    _id: str
    data: Dict[str, str]


class CsvStore:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.csv_path = os.path.join(base_dir, CSV_NAME)
        self.key_path = os.path.join(base_dir, KEY_FILE_NAME)
        self.rows: List[DemandRow] = []
        self._crypto_key = self._load_or_create_key()
        self.load()

    def _load_or_create_key(self) -> bytes:
        env_key = (os.environ.get("DEMANDAS_APP_KEY") or "").strip()
        if env_key:
            raw = base64.urlsafe_b64decode(env_key.encode("utf-8"))
            if len(raw) < 32:
                raise ValueError("DEMANDAS_APP_KEY inválida: esperado ao menos 32 bytes decodificados em base64")
            return raw[:32]

        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                raw = f.read()
            if len(raw) < 32:
                raise ValueError("Arquivo de chave inválido")
            return raw[:32]

        raw = os.urandom(32)
        with open(self.key_path, "wb") as f:
            f.write(raw)
        try:
            os.chmod(self.key_path, 0o600)
        except Exception:
            pass
        return raw

    def _persist_key(self, key: bytes) -> None:
        try:
            with open(self.key_path, "wb") as f:
                f.write(key)
            os.chmod(self.key_path, 0o600)
        except Exception:
            pass

    def _iter_fallback_keys(self) -> List[bytes]:
        seen_paths = set()
        candidates: List[str] = []
        current = os.path.abspath(self.base_dir)

        for _ in range(6):
            key_candidate = os.path.join(current, KEY_FILE_NAME)
            legacy_candidate = os.path.join(current, "legacy", KEY_FILE_NAME)
            for path in (key_candidate, legacy_candidate):
                norm = os.path.normcase(os.path.normpath(path))
                if norm not in seen_paths:
                    seen_paths.add(norm)
                    candidates.append(path)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

        out: List[bytes] = []
        current_key = self._crypto_key[:32]
        for path in candidates:
            if not os.path.exists(path):
                continue
            try:
                raw = open(path, "rb").read()
            except Exception:
                continue
            key = raw[:32]
            if len(key) < 32 or key == current_key:
                continue
            if key not in out:
                out.append(key)
        return out

    @staticmethod
    def _decrypt_with_key(payload: bytes, key: bytes) -> bytes:
        packed = payload[len(ENC_MAGIC) + 1 :].strip()
        raw = base64.urlsafe_b64decode(packed)
        if len(raw) < 16 + 32:
            raise ValueError("Arquivo criptografado inválido")

        nonce = raw[:16]
        mac = raw[-32:]
        cipher = raw[16:-32]
        expected = hmac.new(key, ENC_MAGIC + nonce + cipher, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            raise ValueError("Falha de integridade no arquivo criptografado")

        out = bytearray(len(cipher))
        counter = 0
        offset = 0
        while offset < len(cipher):
            block = hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest()
            n = min(32, len(cipher) - offset)
            for i in range(n):
                out[offset + i] = cipher[offset + i] ^ block[i]
            offset += n
            counter += 1
        return bytes(out)

    def _encrypt_bytes(self, plain: bytes) -> bytes:
        nonce = os.urandom(16)
        out = bytearray(len(plain))
        counter = 0
        offset = 0
        while offset < len(plain):
            block = hashlib.sha256(self._crypto_key + nonce + counter.to_bytes(8, "big")).digest()
            n = min(32, len(plain) - offset)
            for i in range(n):
                out[offset + i] = plain[offset + i] ^ block[i]
            offset += n
            counter += 1
        cipher = bytes(out)
        mac = hmac.new(self._crypto_key, ENC_MAGIC + nonce + cipher, hashlib.sha256).digest()
        return ENC_MAGIC + b"\n" + base64.urlsafe_b64encode(nonce + cipher + mac)

    def _decrypt_bytes(self, payload: bytes) -> bytes:
        if not payload.startswith(ENC_MAGIC + b"\n"):
            return payload
        try:
            return self._decrypt_with_key(payload, self._crypto_key)
        except ValueError as exc:
            if str(exc) != "Falha de integridade no arquivo criptografado":
                raise

        for fallback_key in self._iter_fallback_keys():
            try:
                plain = self._decrypt_with_key(payload, fallback_key)
            except ValueError:
                continue
            self._crypto_key = fallback_key
            self._persist_key(fallback_key)
            return plain

        raise ValueError("Falha de integridade no arquivo criptografado")

    def _read_csv_text(self) -> str:
        if not os.path.exists(self.csv_path):
            return ""
        with open(self.csv_path, "rb") as f:
            payload = f.read()
        plain = self._decrypt_bytes(payload)
        return plain.decode("utf-8")

    def _write_csv_text(self, text: str):
        tmp = self.csv_path + ".tmp"
        payload = self._encrypt_bytes(text.encode("utf-8"))
        with open(tmp, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.csv_path)

    def ensure_exists(self):
        if not os.path.exists(self.csv_path):
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, delimiter=DELIMITER)
            w.writeheader()
            self._write_csv_text(buf.getvalue())

    def load(self):
        self.ensure_exists()
        self.rows = []
        csv_text = self._read_csv_text()
        r = csv.DictReader(io.StringIO(csv_text), delimiter=DELIMITER)
        next_numeric_id = 1
        used_numeric_ids = set()

        for i, row in enumerate(r, start=2):
            for old, new in LEGACY_TO_NEW.items():
                if old in row and new not in row:
                    row[new] = row.get(old, "")

            _id = row.get("_id") or str(uuid.uuid4())
            row["_id"] = _id

            raw_numeric_id = str(row.get("ID") or "").strip()
            try:
                numeric_id = int(raw_numeric_id)
            except (TypeError, ValueError):
                numeric_id = None

            if numeric_id is not None and numeric_id > 0 and numeric_id not in used_numeric_ids:
                row["ID"] = str(numeric_id)
                used_numeric_ids.add(numeric_id)
                next_numeric_id = max(next_numeric_id, numeric_id + 1)
            else:
                while next_numeric_id in used_numeric_ids:
                    next_numeric_id += 1
                row["ID"] = str(next_numeric_id)
                used_numeric_ids.add(next_numeric_id)
                next_numeric_id += 1

            for c in CSV_COLUMNS:
                row.setdefault(c, "")

            try:
                normalized = validate_payload(row, mode="create")
            except ValidationError as e:
                raise ValidationError(f"Erro no arquivo de dados, linha {i}: {e}") from e

            normalized["_id"] = _id
            self.rows.append(DemandRow(_id=_id, data=normalized))

        self.save()

    def _atomic_save(self):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, delimiter=DELIMITER)
        w.writeheader()
        for dr in self.rows:
            w.writerow({c: dr.data.get(c, "") for c in CSV_COLUMNS})
        self._write_csv_text(buf.getvalue())

    def save(self):
        for dr in self.rows:
            dr.data["Prazo"] = normalize_prazo_text(dr.data.get("Prazo", ""))
        self._atomic_save()

    def _next_numeric_id(self) -> str:
        used_ids = set()
        for dr in self.rows:
            try:
                numeric_id = int(str(dr.data.get("ID") or "").strip())
            except (TypeError, ValueError):
                continue
            if numeric_id > 0:
                used_ids.add(numeric_id)

        return str(max(used_ids) + 1) if used_ids else "1"

    def add(self, payload: Dict[str, str]) -> str:
        payload = _map_legacy_keys(payload)
        payload = validate_payload(payload, mode="create")


        _id = str(uuid.uuid4())
        row = {c: "" for c in CSV_COLUMNS}
        row["_id"] = _id
        row["ID"] = self._next_numeric_id()
        for k, v in payload.items():
            if k in row:
                row[k] = v if v is not None else ""
        row["Prazo"] = normalize_prazo_text(row.get("Prazo", ""))

        self.rows.append(DemandRow(_id=_id, data=row))
        self.save()
        return _id

    def update(self, _id: str, changes: Dict[str, str]) -> None:
        changes = _map_legacy_keys(changes)
        changes = validate_payload(changes, mode="update")

        # encontra registro atual
        dr = self.get(_id)
        if not dr:
            raise ValueError("Registro não encontrado")

        # aplica mudanças em uma cópia para validar consistência
        merged = dict(dr.data)
        merged.update({k: (v if v is not None else "") for k, v in changes.items()})

        merged = validate_payload(merged, mode="create")

        # grava de fato
        dr.data.update(merged)
        if "Prazo" in merged:
            dr.data["Prazo"] = normalize_prazo_text(dr.data.get("Prazo", ""))

        self.save()

    def get(self, _id: str) -> Optional[DemandRow]:
        for dr in self.rows:
            if dr._id == _id:
                return dr
        return None

    def delete_by_id(self, _id: str) -> bool:
        before = len(self.rows)
        self.rows = [r for r in self.rows if r._id != _id]
        if len(self.rows) == before:
            return False
        self.save()
        return True
        
    def delete_by_line(self, line: int) -> bool:
        """
        Exclui pelo 'ID' conforme exibido na UI (ordem do build_view()).
        Retorna False se a linha for inválida.
        """
        try:
            line = int(line)
        except Exception:
            return False

        if line < 1:
            return False

        # garante estado atualizado
        self.load()

        view = self.build_view()
        if line > len(view):
            return False

        _id = view[line - 1].get("_id")
        if not _id:
            return False

        return self.delete_by_id(_id)

    def _sorted(self, demands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def key(d):
            dr_dt = d.get("_data_registro_date") or date(9999, 12, 31)
            return (priority_rank(d.get("Prioridade", "")), dr_dt, d.get("_id", ""))
        return sorted(demands, key=key)

    def build_view(self) -> List[Dict[str, Any]]:
        today = date.today()
        out: List[Dict[str, Any]] = []
        for dr in self.rows:
            data = dr.data
            prazos = parse_prazos_list(data.get("Prazo", ""))
            conclusao = parse_ddmmyyyy(data.get("Data Conclusão", ""))
            registro = parse_ddmmyyyy(data.get("Data de Registro", ""))
            timing = calc_timing(data.get("Status", ""), prazos, conclusao, today)

            out.append({
                "_id": dr._id,
                "ID": str(data.get("ID", "") or ""),
                "É Urgente?": data.get("É Urgente?", ""),
                "Status": data.get("Status", ""),
                "Timing": timing,
                "Prioridade": data.get("Prioridade", ""),
                "Data de Registro": data.get("Data de Registro", ""),
                "Prazo": prazo_display(data.get("Prazo", "")),
                "Data Conclusão": data.get("Data Conclusão", ""),
                "Projeto": data.get("Projeto", ""),
                "Descrição": data.get("Descrição", ""),
                "Comentário": data.get("Comentário", ""),
                "ID Azure": data.get("ID Azure", ""),
                "% Conclusão": percent_display(data.get("% Conclusão", "")),
                "Responsável": data.get("Responsável", ""),
                "Reportar?": data.get("Reportar?", ""),
                "Nome": data.get("Nome", ""),
                "Time/Função": data.get("Time/Função", ""),
                "eisenhower_column": data.get("eisenhower_column", ""),
                "_data_registro_date": registro,
                "_prazos_dates": prazos,
                "_conclusao_date": conclusao,
            })
        return self._sorted(out)

    # filtros
    def tab1_by_prazo_date(self, d: date) -> List[Dict[str, Any]]:
        # mantém a regra atual (pendências por data) do seu projeto
        out: List[Dict[str, Any]] = []
        for x in self.build_view():
            if d not in (x.get("_prazos_dates") or []):
                continue
            status = (x.get("Status") or "").strip()
            if status in ("Concluído", "Cancelado"):
                continue
            # adicional: se estiver "concluído-like", também sai
            if (x.get("Data Conclusão") or "").strip() and (x.get("% Conclusão") or "").strip() == "100%":
                continue
            out.append(x)
        return out

    def tab_pending_all(self) -> List[Dict[str, Any]]:
        return [
            x for x in self.build_view()
            if (x.get("Status") or "").strip() not in ("Concluído", "Cancelado")
        ]

    def tab_concluidas_between(self, start: date, end: date) -> List[Dict[str, Any]]:
        out = []
        for x in self.build_view():
            if (x.get("Status") or "").strip() != "Concluído":
                continue
            cd = x.get("_conclusao_date")
            if cd and start <= cd <= end:
                out.append(x)
        return out

    def tab_concluidas_all(self) -> List[Dict[str, Any]]:
        return [
            x for x in self.build_view()
            if (x.get("Status") or "").strip() == "Concluído"
        ]

    def tab_canceladas_all(self) -> List[Dict[str, Any]]:
        return [
            x for x in self.build_view()
            if (x.get("Status") or "").strip() == "Cancelado"
        ]

    def export_all_to_csv(self, export_path: str, delimiter: str = ",") -> int:
        """
        Exporta todas as demandas existentes para um CSV de saída.
        Retorna a quantidade de linhas exportadas.
        """
        rows = self.build_view()
        return self.export_rows_to_csv(export_path, rows, delimiter=delimiter)

    def export_rows_to_csv(self, export_path: str, rows: List[Dict[str, Any]], delimiter: str = ",") -> int:
        """
        Exporta as linhas informadas para um CSV de saída.
        Retorna a quantidade de linhas exportadas.
        """
        # utf-8-sig adiciona BOM para melhorar compatibilidade com Excel,
        # evitando caracteres acentuados corrompidos ao abrir o CSV.
        with open(export_path, "w", newline="", encoding="utf-8-sig") as f:
            f.write(f"{EXPORT_VERSION_PREFIX}{EXPORT_TEMPLATE_VERSION}\n")
            writer = csv.DictWriter(f, fieldnames=DISPLAY_COLUMNS, delimiter=delimiter)
            writer.writeheader()
            for row in rows:
                payload = {col: row.get(col, "") for col in DISPLAY_COLUMNS}
                prazo = str(payload.get("Prazo", "") or "")
                flat_prazo = (
                    prazo.replace("*", "")
                    .replace("\r\n", ",")
                    .replace("\r", ",")
                    .replace("\n", ",")
                )
                payload["Prazo"] = ",".join([p.strip() for p in flat_prazo.split(",") if p.strip()])
                writer.writerow(payload)
        return len(rows)

    def import_from_exported_csv(self, import_path: str, delimiter: str = ",") -> int:
        """
        Importa demandas de um CSV no mesmo formato gerado por export_all_to_csv.
        Substitui as demandas atuais apenas quando todas as linhas são válidas.
        Retorna a quantidade de linhas importadas.
        """
        with open(import_path, "r", newline="", encoding="utf-8-sig") as f:
            imported_rows = self.parse_exported_csv_text(f.read(), delimiter=delimiter)
        return self.replace_with_rows(imported_rows)

    def parse_exported_csv_text(self, csv_text: str, delimiter: str = ",") -> List[DemandRow]:
        normalized_text = csv_text.lstrip("\ufeff")
        version_line = None
        csv_payload_text = normalized_text
        if normalized_text.startswith(EXPORT_VERSION_PREFIX):
            first_break = normalized_text.find("\n")
            if first_break == -1:
                raise ValidationError("CSV exportado inválido: cabeçalho de versão ausente.")
            version_line = normalized_text[:first_break].strip()
            csv_payload_text = normalized_text[first_break + 1 :]
            exported_version = version_line.replace(EXPORT_VERSION_PREFIX, "", 1).strip()
            if exported_version != EXPORT_TEMPLATE_VERSION:
                raise ValidationError(
                    "Versão de template incompatível para importação. Exporte novamente pela versão atual do sistema."
                )

        reader = csv.DictReader(io.StringIO(csv_payload_text), delimiter=delimiter)
        incoming_columns = reader.fieldnames or []
        if incoming_columns != DISPLAY_COLUMNS:
            raise ValidationError(
                "Formato de CSV inválido. Use um arquivo exportado pelo sistema, com as mesmas colunas e ordem."
            )

        imported_rows: List[DemandRow] = []
        imported_used_ids = set()
        imported_next_id = 1
        import_errors: List[str] = []
        for i, row in enumerate(reader, start=2):
            payload = {
                "É Urgente?": (row.get("É Urgente?") or "").strip(),
                "Status": (row.get("Status") or "").strip(),
                "Prioridade": (row.get("Prioridade") or "").strip(),
                "Data de Registro": (row.get("Data de Registro") or "").strip(),
                "Prazo": (row.get("Prazo") or "").strip(),
                "Data Conclusão": (row.get("Data Conclusão") or "").strip(),
                "Projeto": row.get("Projeto") or "",
                "Descrição": row.get("Descrição") or "",
                "Comentário": row.get("Comentário") or "",
                "ID Azure": row.get("ID Azure") or "",
                "% Conclusão": (row.get("% Conclusão") or "").strip(),
                "Responsável": row.get("Responsável") or "",
                "Reportar?": (row.get("Reportar?") or "").strip(),
                "Nome": row.get("Nome") or "",
                "Time/Função": row.get("Time/Função") or "",
                "eisenhower_column": row.get("eisenhower_column") or "",
            }

            try:
                normalized = validate_payload(payload, mode="create")
            except ValidationError as e:
                import_errors.append(f"Erro na linha {i}: {e}")
                continue

            new_id = str(uuid.uuid4())
            data = {c: "" for c in CSV_COLUMNS}
            data["_id"] = new_id

            imported_numeric_id_raw = (row.get("ID") or "").strip()
            imported_numeric_id = int(imported_numeric_id_raw) if imported_numeric_id_raw.isdigit() else None
            if imported_numeric_id is not None and imported_numeric_id > 0 and imported_numeric_id not in imported_used_ids:
                data["ID"] = str(imported_numeric_id)
                imported_used_ids.add(imported_numeric_id)
                imported_next_id = max(imported_next_id, imported_numeric_id + 1)
            else:
                while imported_next_id in imported_used_ids:
                    imported_next_id += 1
                data["ID"] = str(imported_next_id)
                imported_used_ids.add(imported_next_id)
                imported_next_id += 1
            for c in CSV_COLUMNS:
                if c in {"_id", "ID"}:
                    continue
                data[c] = normalized.get(c, "")
            imported_rows.append(DemandRow(_id=new_id, data=data))

        if import_errors:
            raise ValidationError("Importação contém linhas inválidas\n" + "\n".join(import_errors))

        return imported_rows

    def replace_with_rows(self, imported_rows: List[DemandRow]) -> int:
        self.rows = imported_rows
        self.save()
        return len(imported_rows)

    def merge_with_rows(self, imported_rows: List[DemandRow]) -> int:
        merged: List[DemandRow] = []

        for existing in self.rows:
            data = {c: "" for c in CSV_COLUMNS}
            data.update(existing.data)
            data["_id"] = str(uuid.uuid4())
            merged.append(DemandRow(_id=data["_id"], data=data))

        for imported in imported_rows:
            data = {c: "" for c in CSV_COLUMNS}
            data.update(imported.data)
            data["_id"] = str(uuid.uuid4())
            merged.append(DemandRow(_id=data["_id"], data=data))

        for idx, row in enumerate(merged, start=1):
            row.data["ID"] = str(idx)

        self.rows = merged
        self.save()
        return len(imported_rows)

    def export_encrypted_backup_csv(self, backup_path: str, team_control_payload: Dict[str, Any]) -> int:
        """
        Gera um backup CSV criptografado contendo demandas + controle de time.
        Retorna a quantidade de demandas exportadas.
        """
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=DELIMITER)
        writer.writerow(["section", "payload"])
        writer.writerow(["metadata", json.dumps({"version": 1}, ensure_ascii=False)])
        writer.writerow(["team_control", json.dumps(team_control_payload or {}, ensure_ascii=False)])
        for dr in self.rows:
            writer.writerow(["demand", json.dumps(dr.data, ensure_ascii=False)])

        plain = buf.getvalue().encode("utf-8-sig")
        encrypted = self._encrypt_bytes(plain)
        with open(backup_path, "wb") as f:
            f.write(encrypted)
        return len(self.rows)

    def import_encrypted_backup_csv(self, backup_path: str) -> Dict[str, Any]:
        """
        Restaura backup CSV criptografado no formato export_encrypted_backup_csv.
        Substitui as demandas atuais e retorna o payload de team_control.
        """
        with open(backup_path, "rb") as f:
            raw = f.read()
        plain = self._decrypt_bytes(raw)

        reader = csv.DictReader(io.StringIO(plain.decode("utf-8-sig")), delimiter=DELIMITER)
        expected = ["section", "payload"]
        if (reader.fieldnames or []) != expected:
            raise ValidationError("Formato de backup inválido.")

        imported_rows: List[DemandRow] = []
        imported_used_ids = set()
        imported_next_id = 1
        team_control_payload: Dict[str, Any] = {}

        for i, row in enumerate(reader, start=2):
            section = (row.get("section") or "").strip().lower()
            payload_raw = row.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Backup inválido na linha {i}.") from e

            if section == "team_control":
                if isinstance(payload, dict):
                    team_control_payload = payload
                continue

            if section != "demand":
                continue

            if not isinstance(payload, dict):
                raise ValidationError(f"Backup inválido na linha {i}.")

            try:
                normalized = validate_payload(payload, mode="create")
            except ValidationError as e:
                raise ValidationError(f"Erro no backup, linha {i}: {e}") from e

            new_id = str(uuid.uuid4())
            data = {c: "" for c in CSV_COLUMNS}
            data["_id"] = new_id

            imported_numeric_id_raw = str(payload.get("ID") or "").strip()
            imported_numeric_id = int(imported_numeric_id_raw) if imported_numeric_id_raw.isdigit() else None
            if imported_numeric_id is not None and imported_numeric_id > 0 and imported_numeric_id not in imported_used_ids:
                data["ID"] = str(imported_numeric_id)
                imported_used_ids.add(imported_numeric_id)
                imported_next_id = max(imported_next_id, imported_numeric_id + 1)
            else:
                while imported_next_id in imported_used_ids:
                    imported_next_id += 1
                data["ID"] = str(imported_next_id)
                imported_used_ids.add(imported_next_id)
                imported_next_id += 1
            for c in CSV_COLUMNS:
                if c in {"_id", "ID"}:
                    continue
                data[c] = normalized.get(c, "")
            imported_rows.append(DemandRow(_id=new_id, data=data))

        self.rows = imported_rows
        self.save()
        return team_control_payload
