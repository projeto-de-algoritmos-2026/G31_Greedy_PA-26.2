from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import cached_property

from src.dados import Setor, Unidade, carregar_setores, carregar_unidades
from src.geometria import distancia_km


@dataclass(frozen=True)
class Instancia:
    unidades: list[Unidade]
    setores: list[Setor]
    coberturas: list[frozenset[int]]
    raio_km: float

    @cached_property
    def pesos(self) -> list[int]:
        return [s.populacao for s in self.setores]

    @property
    def populacao_total(self) -> int:
        return sum(s.populacao for s in self.setores)

    @property
    def populacao_alcancavel(self) -> int:
        return self.populacao_de(set().union(*self.coberturas) if self.coberturas else set())

    def populacao_de(self, indices) -> int:
        pesos = self.pesos
        return sum(pesos[i] for i in indices)

    def cobertos_por(self, escolhidas) -> set[int]:
        alcancados: set[int] = set()
        for j in escolhidas:
            alcancados |= self.coberturas[j]
        return alcancados


def montar(unidades: list[Unidade], setores: list[Setor], raio_km: float) -> Instancia:
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
    return montar(carregar_unidades(), carregar_setores(), raio_km)


def _main(argv: list[str]) -> int:
    raio = float(argv[1]) if len(argv) > 1 else 2.0
    try:
        inst = carregar(raio)
    except FileNotFoundError as erro:
        print(f"não encontrei {erro} — veja o README", file=sys.stderr)
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
