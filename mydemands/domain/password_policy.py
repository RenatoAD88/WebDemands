from __future__ import annotations

import re
from typing import List, Tuple


class PasswordPolicy:
    MIN_LENGTH = 6

    @classmethod
    def validate(cls, password: str) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if len(password or "") < cls.MIN_LENGTH:
            errors.append("A senha deve ter pelo menos 6 caracteres.")
        if not re.search(r"[a-z]", password or ""):
            errors.append("A senha deve conter letra minúscula.")
        if not re.search(r"[A-Z]", password or ""):
            errors.append("A senha deve conter letra maiúscula.")
        if not re.search(r"\d", password or ""):
            errors.append("A senha deve conter número.")
        if not re.search(r"[^\w\s]", password or ""):
            errors.append("A senha deve conter caractere especial.")
        return (len(errors) == 0, errors)
