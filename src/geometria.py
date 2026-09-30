"""Geometria no plano e na esfera, sem biblioteca de GIS."""
from __future__ import annotations

import math

#: Raio médio da Terra, em quilômetros.
RAIO_DA_TERRA_KM = 6371.0


def centroide(pontos: list[tuple[float, float]],
              inicios: list[int] | None = None) -> tuple[float, float]:
    """
    Centro de massa de um polígono, pela fórmula do shoelace.

    `pontos` vem do shapefile como uma lista corrida de (x, y) e `inicios`
    diz onde cada anel começa — um setor pode ter várias partes (ilhas) ou
    buracos. Anéis são percorridos em sentidos opostos no formato shapefile,
    então somar as áreas com sinal já desconta os buracos sozinho.

    Cai na média aritmética dos vértices quando a área dá zero, o que
    acontece em polígono degenerado — raro, mas existe em base real.
    """
    if not pontos:
        raise ValueError("polígono sem pontos")

    limites = list(inicios or [0]) + [len(pontos)]
    area_dobrada = soma_x = soma_y = 0.0

    for i in range(len(limites) - 1):
        anel = pontos[limites[i]:limites[i + 1]]
        for j in range(len(anel) - 1):
            x0, y0 = anel[j]
            x1, y1 = anel[j + 1]
            cruzado = x0 * y1 - x1 * y0
            area_dobrada += cruzado
            soma_x += (x0 + x1) * cruzado
            soma_y += (y0 + y1) * cruzado

    if abs(area_dobrada) < 1e-12:
        return (sum(p[0] for p in pontos) / len(pontos),
                sum(p[1] for p in pontos) / len(pontos))

    return soma_x / (3 * area_dobrada), soma_y / (3 * area_dobrada)


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distância de haversine — a que se percorre sobre a superfície da Terra.

    Pitágoras direto em graus erraria: um grau de longitude vale 111 km no
    equador e encolhe conforme se afasta dele. No DF, a -15,8°, vale 107 km.
    """
    fi1, fi2 = math.radians(lat1), math.radians(lat2)
    dfi = fi2 - fi1
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dfi / 2) ** 2 + math.cos(fi1) * math.cos(fi2) * math.sin(dlambda / 2) ** 2
    return 2 * RAIO_DA_TERRA_KM * math.asin(math.sqrt(a))
