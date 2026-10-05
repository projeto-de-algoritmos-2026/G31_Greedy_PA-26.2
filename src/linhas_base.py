
from __future__ import annotations

import random
import sys

from src.cobertura import Instancia
from src.geometria import distancia_km


def maiores_sozinhas(inst: Instancia, k: int) -> list[int]:

    ordem = sorted(range(len(inst.unidades)),
                   key=lambda j: inst.populacao_de(inst.coberturas[j]),
                   reverse=True)
    return ordem[:k]


def centro_populacional(inst: Instancia) -> tuple[float, float]:

    peso_total = inst.populacao_total
    if peso_total == 0:
        raise ValueError("população total é zero")
    lat = sum(s.lat * s.populacao for s in inst.setores) / peso_total
    lon = sum(s.lon * s.populacao for s in inst.setores) / peso_total
    return lat, lon


def mais_centrais(inst: Instancia, k: int) -> list[int]:
    """As `k` unidades mais próximas do centro populacional."""
    lat, lon = centro_populacional(inst)
    ordem = sorted(range(len(inst.unidades)),
                   key=lambda j: distancia_km(lat, lon,
                                              inst.unidades[j].lat,
                                              inst.unidades[j].lon))
    return ordem[:k]


def aleatorias(inst: Instancia, k: int, semente: int = 42) -> list[int]:

    sorteio = random.Random(semente)
    total = len(inst.unidades)
    return sorteio.sample(range(total), min(k, total))


def media_aleatoria(inst: Instancia, k: int, repeticoes: int = 30,
                    semente: int = 42) -> float:

    if repeticoes <= 0:
        raise ValueError("repeticoes precisa ser positivo")
    sorteio = random.Random(semente)
    total = len(inst.unidades)
    soma = 0
    for _ in range(repeticoes):
        escolhidas = sorteio.sample(range(total), min(k, total))
        soma += inst.populacao_de(inst.cobertos_por(escolhidas))
    return soma / repeticoes


LINHAS_DE_BASE = {
    "maiores sozinhas": maiores_sozinhas,
    "mais centrais": mais_centrais,
    "aleatórias": aleatorias,
}


def _main(argv: list[str]) -> int:
    from src.cobertura import carregar

    k = int(argv[1]) if len(argv) > 1 else 20
    raio = float(argv[2]) if len(argv) > 2 else 2.0
    try:
        inst = carregar(raio)
    except FileNotFoundError as erro:
        print(f"não encontrei {erro} — veja data/README.md", file=sys.stderr)
        return 1
    except ImportError as erro:
        print(erro, file=sys.stderr)
        return 1

    total = inst.populacao_total
    lat, lon = centro_populacional(inst)
    print(f"k = {k} unidades · raio de {raio:g} km")
    print(f"centro populacional: {lat:.4f}, {lon:.4f}\n")

    for nome, escolher in LINHAS_DE_BASE.items():
        coberta = inst.populacao_de(inst.cobertos_por(escolher(inst, k)))
        print(f"  {nome:<18} {coberta:>9,}  ({coberta/total:>5.1%})".replace(",", "."))

    media = media_aleatoria(inst, k)
    print(f"  {'aleatórias (30x)':<18} {media:>9,.0f}  ({media/total:>5.1%})"
          .replace(",", "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
