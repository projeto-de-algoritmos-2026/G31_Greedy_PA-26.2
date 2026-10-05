
from __future__ import annotations

import sys
from dataclasses import dataclass

from src.cobertura import Instancia


@dataclass(frozen=True)
class PassoGuloso:

    unidade: int
    ganho: int
    acumulado: int
    setores_novos: frozenset[int]


def _validar_k(k: int) -> None:
    if not isinstance(k, int):
        raise TypeError("k precisa ser um inteiro")
    if k < 0:
        raise ValueError("k precisa ser maior ou igual a zero")


def _ganho(inst: Instancia, unidade: int, cobertos: set[int]) -> tuple[int, set[int]]:

    novos = set(inst.coberturas[unidade]) - cobertos
    return inst.populacao_de(novos), novos


def historico(inst: Instancia, k: int) -> list[PassoGuloso]:

    _validar_k(k)

    limite = min(k, len(inst.unidades))
    escolhidas: set[int] = set()
    cobertos: set[int] = set()
    resultado: list[PassoGuloso] = []
    acumulado = 0

    for _ in range(limite):
        melhor_unidade: int | None = None
        melhor_ganho = -1
        melhor_novos: set[int] = set()

        for unidade in range(len(inst.unidades)):
            if unidade in escolhidas:
                continue

            ganho, novos = _ganho(inst, unidade, cobertos)

            # Em empate, menor índice torna o resultado determinístico.
            if ganho > melhor_ganho:
                melhor_unidade = unidade
                melhor_ganho = ganho
                melhor_novos = novos

        # Só não acontece se não houver unidades disponíveis.
        if melhor_unidade is None:
            break

        escolhidas.add(melhor_unidade)
        cobertos.update(melhor_novos)
        acumulado += melhor_ganho
        resultado.append(
            PassoGuloso(
                unidade=melhor_unidade,
                ganho=melhor_ganho,
                acumulado=acumulado,
                setores_novos=frozenset(melhor_novos),
            )
        )

    return resultado


def guloso(inst: Instancia, k: int) -> list[int]:

    return [passo.unidade for passo in historico(inst, k)]


def populacao_coberta(inst: Instancia, k: int) -> int:
  
    escolhidas = guloso(inst, k)
    return inst.populacao_de(inst.cobertos_por(escolhidas))


def _main(argv: list[str]) -> int:
    from src.cobertura import carregar

    k = int(argv[1]) if len(argv) > 1 else 20
    raio = float(argv[2]) if len(argv) > 2 else 2.0

    try:
        inst = carregar(raio)
    except FileNotFoundError as erro:
        print(f"não encontrei {erro} — veja o README", file=sys.stderr)
        return 1
    except ImportError as erro:
        print(erro, file=sys.stderr)
        return 1

    passos = historico(inst, k)
    coberta = passos[-1].acumulado if passos else 0
    total = inst.populacao_total

    print(f"k = {len(passos)} unidades · raio de {raio:g} km")
    print(f"população coberta: {coberta:,} ({coberta / total:.1%})".replace(",", "."))
    print("\nordem de escolha:")
    for numero, passo in enumerate(passos, 1):
        unidade = inst.unidades[passo.unidade]
        print(
            f"  {numero:>2}. {passo.unidade:>3} · {unidade.nome}"
            f" · +{passo.ganho:,} · {passo.acumulado:,}".replace(",", ".")
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
