from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass
 
from src.cobertura import Instancia
from src.geometria import distancia_km
 
 
def custo_simulado(inst: Instancia, semente: int = 7) -> list[float]:
    sorteio = random.Random(semente)
    custos = []
    for cobertura in inst.coberturas:
        base = 50_000 + 1_500 * len(cobertura)
        ruido = sorteio.uniform(0.85, 1.15)
        custos.append(round(base * ruido, 2))
    return custos
 
 
def valor_local(inst: Instancia) -> list[int]:

    valores = []
    for u in inst.unidades:
        mais_perto = min(
            inst.setores,
            key=lambda s: distancia_km(u.lat, u.lon, s.lat, s.lon),
        )
        valores.append(mais_perto.populacao)
    return valores
 
 
COLUNAS_MAXIMAS = 5_000


def _reais(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


@dataclass(frozen=True)
class ResultadoMochila:
    escolhidas: list[int]
    valor_total: int
    custo_total: float
 
 
def guloso_mochila(valores: list[int], custos: list[float], orcamento: float) -> ResultadoMochila:

    n = len(valores)
    indices = sorted(range(n), key=lambda i: valores[i] / custos[i], reverse=True)
 
    escolhidas: list[int] = []
    custo_acumulado = 0.0
    valor_acumulado = 0
    for i in indices:
        if custo_acumulado + custos[i] <= orcamento:
            escolhidas.append(i)
            custo_acumulado += custos[i]
            valor_acumulado += valores[i]
 
    melhor_isolado = max(
        (i for i in range(n) if custos[i] <= orcamento),
        key=lambda i: valores[i], default=None,
    )
 
    if melhor_isolado is not None and valores[melhor_isolado] > valor_acumulado:
        return ResultadoMochila(
            escolhidas=[melhor_isolado],
            valor_total=valores[melhor_isolado],
            custo_total=custos[melhor_isolado],
        )
 
    return ResultadoMochila(
        escolhidas=escolhidas, valor_total=valor_acumulado, custo_total=custo_acumulado,
    )
 
 
def otimo_mochila(valores: list[int], custos: list[float], orcamento: float) -> ResultadoMochila:

    n = len(valores)
    passo = max(1, math.ceil(orcamento / COLUNAS_MAXIMAS))
    capacidade = int(orcamento) // passo
    custos_inteiros = [int(c) // passo for c in custos]

    tabela = [[0] * (capacidade + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        custo_i, valor_i = custos_inteiros[i - 1], valores[i - 1]
        for c in range(capacidade + 1):
            tabela[i][c] = tabela[i - 1][c]
            if custo_i <= c:
                candidato = tabela[i - 1][c - custo_i] + valor_i
                if candidato > tabela[i][c]:
                    tabela[i][c] = candidato
 
    escolhidas = []
    c = capacidade
    for i in range(n, 0, -1):
        if tabela[i][c] != tabela[i - 1][c]:
            escolhidas.append(i - 1)
            c -= custos_inteiros[i - 1]
    escolhidas.reverse()
 
    return ResultadoMochila(
        escolhidas=escolhidas,
        valor_total=tabela[n][capacidade],
        custo_total=sum(custos[i] for i in escolhidas),
    )
 
 
def _main() -> int:
    if len(sys.argv) < 3:
        print("uso: python -m src.mochila <orcamento_reais> <raio_km>", file=sys.stderr)
        return 1
 
    from src.cobertura import carregar
 
    orcamento = float(sys.argv[1])
    raio_km = float(sys.argv[2])
 
    try:
        inst = carregar(raio_km)
    except (FileNotFoundError, ImportError) as erro:
        print(erro, file=sys.stderr)
        return 1
 
    custos = custo_simulado(inst)
    valores = valor_local(inst)
    resultado = guloso_mochila(valores, custos, orcamento)
 
    print(f"Orçamento: R$ {_reais(orcamento)}")
    print(f"Unidades escolhidas: {len(resultado.escolhidas)}")
    print(f"Custo usado: R$ {_reais(resultado.custo_total)}")
    print(f"Valor (população local somada): {resultado.valor_total:,}".replace(",", "."))
    for i in resultado.escolhidas:
        print(f"  - {inst.unidades[i].nome} (custo simulado R$ {_reais(custos[i])})")
    return 0
 
 
if __name__ == "__main__":
    raise SystemExit(_main())
 