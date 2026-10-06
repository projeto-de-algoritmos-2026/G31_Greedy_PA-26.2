
from __future__ import annotations

import itertools
import sys

from src.cobertura import Instancia


def _validar_k(k: int) -> None:
    if not isinstance(k, int):
        raise TypeError("k precisa ser um inteiro")
    if k < 0:
        raise ValueError("k precisa ser maior ou igual a zero")


def exato(inst: Instancia, k: int) -> list[int]:

    _validar_k(k)

    n = len(inst.unidades)
    limite = min(k, n)
    if limite == 0 or n == 0:
        return []

    melhor: tuple[int, ...] = ()
    melhor_populacao = -1

    for combinacao in itertools.combinations(range(n), limite):
        cobertos = inst.cobertos_por(combinacao)
        populacao = inst.populacao_de(cobertos)
        if populacao > melhor_populacao:
            melhor_populacao = populacao
            melhor = combinacao

    return list(melhor)


def populacao_coberta(inst: Instancia, k: int) -> int:

    return inst.populacao_de(inst.cobertos_por(exato(inst, k)))


def _main(argv: list[str]) -> int:
    from src.cobertura import carregar

    k = int(argv[1]) if len(argv) > 1 else 8
    raio = float(argv[2]) if len(argv) > 2 else 2.0

    try:
        inst = carregar(raio)
    except FileNotFoundError as erro:
        print(f"não encontrei {erro} — veja o README", file=sys.stderr)
        return 1
    except ImportError as erro:
        print(erro, file=sys.stderr)
        return 1

    escolhidas = exato(inst, k)
    coberta = inst.populacao_de(inst.cobertos_por(escolhidas))
    total = inst.populacao_total

    print(f"k = {len(escolhidas)} unidades · raio de {raio:g} km")
    print(f"população coberta: {coberta:,} ({coberta / total:.1%})".replace(",", "."))
    print(f"índices escolhidos: {escolhidas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
