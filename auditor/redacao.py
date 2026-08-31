"""
Camada de redacao. Nasceu de um risco concreto, nao de conformidade abstrata.

O repositorio principal deste projeto e PUBLICO, e os artefatos de auditoria
carregam material do cliente. Se "nao publicar query real" depender de quem
escreve o relatorio lembrar, um dia nao lembra.

REGRA: query e documento NUNCA entram em artefato por caminho automatico.
O que entra e o hash. Exemplo em claro so existe quando o operador pede
explicitamente, e mesmo assim passa pelo detector de segredo.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

# Padroes de segredo. Barram mesmo com `exemplos_em_claro=True`: o operador
# pode autorizar mostrar texto do cliente, nao pode autorizar vazar credencial.
SEGREDOS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),         "ANTHROPIC_KEY"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"),                "API_KEY"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),         "GITHUB_TOKEN"),
    (re.compile(r"AKIA[0-9A-Z]{16}"),                   "AWS_KEY"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\."), "JWT"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "PRIVATE_KEY"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"),         "EMAIL"),
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),      "CPF"),
]


def hash_curto(t: str, n: int = 12) -> str:
    return hashlib.sha256((t or "").encode("utf-8")).hexdigest()[:n]


def varre_segredos(t: str) -> list[str]:
    return sorted({r for p, r in SEGREDOS if p.search(t or "")})


def limpa(t: str) -> str:
    for p, rot in SEGREDOS:
        t = p.sub(f"[{rot}_REMOVIDO]", t or "")
    return t


class Politica:
    """
    Como o material do cliente aparece nos artefatos.

    `exemplos_em_claro=False` (default) e o modo publicavel: so hash e id.
    """

    def __init__(self, exemplos_em_claro: bool = False, max_chars: int = 160):
        self.exemplos_em_claro = exemplos_em_claro
        self.max_chars = max_chars
        self.removidos: list[str] = []

    def texto(self, t: str, rotulo: str = "texto") -> str:
        achados = varre_segredos(t)
        if achados:
            self.removidos.extend(achados)
        if not self.exemplos_em_claro:
            return f"<{rotulo}:{hash_curto(t)}>"
        return limpa(t)[:self.max_chars]

    def query(self, q: str) -> str:
        return self.texto(q, "query")

    def documento(self, d: str) -> str:
        return self.texto(d, "doc")

    def sanitiza(self, obj: Any) -> Any:
        """
        Ultima barreira antes de gravar: varre a estrutura inteira e limpa
        segredo de QUALQUER string, inclusive de campos que ninguem previu.
        """
        if isinstance(obj, str):
            a = varre_segredos(obj)
            if a:
                self.removidos.extend(a)
                return limpa(obj)
            return obj
        if isinstance(obj, dict):
            return {k: self.sanitiza(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self.sanitiza(v) for v in obj]
        return obj

    def relatorio(self) -> dict[str, Any]:
        c = sorted(set(self.removidos))
        return {
            "exemplos_em_claro": self.exemplos_em_claro,
            "segredos_removidos": c,
            "n_ocorrencias": len(self.removidos),
            "nota": ("query e documento aparecem como hash; texto em claro so "
                     "com --exemplos-em-claro, e segredo e removido nos dois modos"),
        }
