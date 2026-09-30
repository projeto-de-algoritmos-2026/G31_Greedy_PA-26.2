"""
Quem cobre quem: a ponte entre os dados e o algoritmo.

Fixado um raio, cada unidade de saúde cobre o conjunto de setores cujo
centro está a essa distância ou menos. É essa estrutura que o guloso
consome — ele nunca toca em latitude nem em quilômetro, só em conjuntos.

    python -m src.cobertura 2.0
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

from src.dados import Setor, Unidade, carregar_setores, carregar_unidades
from src.geometria import distancia_km


@dataclass(frozen=True)
class Instancia:
    """
    Um problema de cobertura máxima pronto para ser resolvido.

    `coberturas[j]` são os índices dos setores que a unidade `j` alcança, e
    `pesos[i]` é a população do setor `i`. O algoritmo precisa só disso.
    """
    unidades: list[Unidade]
    setores: list[Setor]
    coberturas: list[frozenset[int]]
    raio_km: float

    @property
    def pesos(self) -> list[int]:
        return [s.populacao for s in self.setores]

    @property
    def populacao_total(self) -> int:
        return sum(s.populacao for s in self.setores)

    @property
    def populacao_alcancavel(self) -> int:
        """
        Quanto dá para cobrir usando TODAS as unidades.

        É o teto do problema, e não é a população inteira: há setores fora
        do alcance de qualquer unidade. Comparar um resultado com a
        população total, e não com este número, subestima o algoritmo.
        """
        return self.populacao_de(set().union(*self.coberturas) if self.coberturas else set())

    def populacao_de(self, indices) -> int:
        """População somada de um conjunto de setores."""
        pesos = self.pesos
        return sum(pesos[i] for i in indices)

    def cobertos_por(self, escolhidas) -> set[int]:
        """União dos setores alcançados por um conjunto de unidades."""
        alcancados: set[int] = set()
        for j in escolhidas:
            alcancados |= self.coberturas[j]
        return alcancados


def montar(unidades: list[Unidade], setores: list[Setor], raio_km: float) -> Instancia:
    """
    Calcula, para cada unidade, quais setores ela alcança.

    São 200 × 5.418 distâncias, pouco mais de um milhão — roda em menos de
    um segundo, então não vale a pena um índice espacial aqui. Se o
    problema crescesse para um estado inteiro, valeria.
    """
    if raio_km <= 0:
        raise ValueError(f"raio precisa ser positivo, recebi {raio_km}")

    coberturas = [
        frozenset(
            i for i, s in enumerate(setores)
            if distancia_km(u.lat, u.lon, s.lat, s.lon) <= raio_km
        )
        for u in unidades
    ]
    return Instancia(unidades=unidades, setores=setores,
                     coberturas=coberturas, raio_km=raio_km)


def carregar(raio_km: float) -> Instancia:
    """Atalho: lê as duas bases e monta a instância."""
    return montar(carregar_unidades(), carregar_setores(), raio_km)


def _main(argv: list[str]) -> int:
    raio = float(argv[1]) if len(argv) > 1 else 2.0
    try:
        inst = carregar(raio)
    except FileNotFoundError as erro:
        print(f"não encontrei {erro} — veja data/README.md", file=sys.stderr)
        return 1
    except ImportError as erro:
        print(erro, file=sys.stderr)
        return 1

    total = inst.populacao_total
    alcancavel = inst.populacao_alcancavel
    vazias = sum(1 for c in inst.coberturas if not c)
    tamanhos = sorted(len(c) for c in inst.coberturas)

    print(f"raio de {raio:g} km")
    print(f"  população do DF        {total:>10,}".replace(",", "."))
    print(f"  alcançável por alguma  {alcancavel:>10,}  ({alcancavel/total:.1%})"
          .replace(",", "."))
    print(f"  fora de todo alcance   {total - alcancavel:>10,}"
          .replace(",", "."))
    print(f"\n  setores por unidade: mínimo {tamanhos[0]}, "
          f"mediana {tamanhos[len(tamanhos)//2]}, máximo {tamanhos[-1]}")
    if vazias:
        print(f"  {vazias} unidades não alcançam setor nenhum")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
