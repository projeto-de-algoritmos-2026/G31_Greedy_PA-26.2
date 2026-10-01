"""
Validação: o guloso vale a pena?

    python validacao.py
    python validacao.py --raio 3 --kmax 80
    python validacao.py --so-mapa --kmapa 40

A rodada completa leva uns vinte segundos, quase todos na força bruta. O
`--so-mapa` pula tudo e desenha só o mapa, em cerca de um segundo — é o
modo de olhar o resultado mudando de `k` e de raio sem esperar.

Responde três perguntas, nesta ordem de importância:

1. O guloso ganha das escolhas óbvias? (contra as linhas de base)
2. Quão longe ele fica do ótimo? (contra a força bruta, em instâncias
   reduzidas — na instância completa isso é inviável)
3. O ganho de cada unidade nova diminui? (a submodularidade, que é a
   propriedade de onde sai a garantia de 1−1/e)

Grava gráficos, tabela e dados brutos em `resultados/`.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

from src.cobertura import Instancia, montar
from src.exato import exato
from src.guloso import guloso, historico
from src.linhas_base import LINHAS_DE_BASE

SAIDA = Path("resultados")

#: Superfície clara e tokens de texto. Validados com
#: `scripts/validate_palette.js --mode light`.
SURFACE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
GRADE = "#e4e3df"

#: Slots 1 a 4 da paleta categórica. O guloso fica no slot 1; as linhas de
#: base nos seguintes. Dois deles ficam abaixo de 3:1 de contraste na
#: superfície clara, o que obriga rótulo visível — por isso cada série é
#: rotulada diretamente, sem caixa de legenda.
COR = {
    "guloso": "#2a78d6",
    "maiores sozinhas": "#eb6834",
    "aleatórias": "#1baf7a",
    "mais centrais": "#eda100",
}

#: No mapa só há duas categorias, e a segunda é ausência: setor que
#: ninguém alcança fica em cinza neutro, nunca numa segunda cor da paleta.
#: Um cinza vale "sem dado"; uma cor valeria "outra coisa". Este tom é o
#: mais claro que ainda passa de 3:1 de contraste na superfície clara.
SEM_COBERTURA = "#8b8984"

#: Um grau de latitude são 111 km em qualquer lugar. É o mesmo número que
#: a `geometria` usa implicitamente pelo raio da Terra, e aqui serve só
#: para desenhar o raio de cobertura na escala certa.
KM_POR_GRAU = 111.0


@dataclass
class Comparacao:
    """O guloso contra o ótimo, numa instância reduzida."""
    candidatos: int
    k: int
    guloso: int
    otimo: int

    @property
    def razao(self) -> float:
        return self.guloso / self.otimo if self.otimo else 1.0


def curva(inst: Instancia, kmax: int) -> dict[str, list[int]]:
    """
    População coberta por cada estratégia, para k de 1 até kmax.

    O guloso sai de uma passada só: `historico` já devolve o acumulado de
    cada rodada. As linhas de base precisam ser recalculadas por k, porque
    não são incrementais — a melhor escolha de 10 não contém a de 9.
    """
    passos = historico(inst, kmax)
    series = {"guloso": [p.acumulado for p in passos]}

    for nome, escolher in LINHAS_DE_BASE.items():
        series[nome] = [
            inst.populacao_de(inst.cobertos_por(escolher(inst, k)))
            for k in range(1, len(passos) + 1)
        ]
    return series


def contra_o_otimo(inst: Instancia, instancias: int = 12,
                   semente: int = 42) -> list[Comparacao]:
    """
    Compara guloso e ótimo em instâncias reduzidas.

    Na instância completa a força bruta é inviável. Com 200 unidades,
    k = 3 são 1.313.400 combinações e levam cerca de 107 segundos — uns
    80 microssegundos cada. Em k = 8 são 55.098.996.177.225 combinações,
    e no mesmo ritmo isso passa de cento e quarenta anos.

    Por isso sorteamos subconjuntos de candidatos pequenos o bastante
    para o ótimo ser calculável.
    """
    sorteio = random.Random(semente)
    disponiveis = len(inst.unidades)
    comparacoes = []
    for _ in range(instancias):
        # os tamanhos abaixo são os da instância real; numa menor, o que
        # houver. Sem isto, `sample` estoura em instância pequena.
        m = min(sorteio.choice([20, 25, 30]), disponiveis)
        k = min(sorteio.choice([2, 3, 4]), m)
        indices = sorteio.sample(range(disponiveis), m)
        reduzida = montar([inst.unidades[j] for j in indices],
                          inst.setores, inst.raio_km)
        comparacoes.append(Comparacao(
            candidatos=m, k=k,
            guloso=reduzida.populacao_de(reduzida.cobertos_por(guloso(reduzida, k))),
            otimo=reduzida.populacao_de(reduzida.cobertos_por(exato(reduzida, k))),
        ))
    return comparacoes


def _escapar(texto: str) -> str:
    return (texto.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def grafico_curva(series: dict[str, list[int]], total: int, raio: float) -> str:
    """Linhas: população coberta conforme o número de unidades cresce."""
    L, T = 92, 74
    larg, alt = 560, 300
    # 176 à direita, e não 150: o rótulo mais longo é
    # "maiores sozinhas · 58%", que encostava na borda
    W, H = L + larg + 176, T + alt + 64
    kmax = len(series["guloso"])
    teto = max(max(v) for v in series.values()) / total

    def x(k):   return L + (k - 1) / max(kmax - 1, 1) * larg
    def y(frac): return T + alt - (frac / teto) * alt

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="system-ui, -apple-system, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>',
         f'<text x="{L}" y="30" font-size="15" font-weight="600" fill="{TEXTO}">'
         f'Quanta gente cada estratégia alcança</text>',
         f'<text x="{L}" y="50" font-size="12" fill="{TEXTO_2}">'
         f'Distrito Federal · raio de {raio:g} km · '
         f'{total:,}'.replace(",", ".") + ' habitantes</text>']

    for frac in [i / 10 for i in range(0, 11)]:
        if frac > teto:
            break
        yy = y(frac)
        p.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{L+larg}" y2="{yy:.1f}" '
                 f'stroke="{GRADE}" stroke-width="1"/>')
        p.append(f'<text x="{L-10}" y="{yy+4:.1f}" font-size="11" fill="{TEXTO_2}" '
                 f'text-anchor="end">{frac:.0%}</text>')

    for k in range(10, kmax + 1, 10):
        p.append(f'<text x="{x(k):.1f}" y="{T+alt+22}" font-size="11" '
                 f'fill="{TEXTO_2}" text-anchor="middle">{k}</text>')
    p.append(f'<text x="{L+larg/2:.0f}" y="{T+alt+46}" font-size="12" '
             f'fill="{TEXTO_2}" text-anchor="middle">unidades escolhidas</text>')

    ordem = sorted(series, key=lambda n: -series[n][-1])
    for i, nome in enumerate(ordem):
        valores = series[nome]
        pontos = " ".join(f"{x(k+1):.1f},{y(v/total):.1f}"
                          for k, v in enumerate(valores))
        largura = 2.5 if nome == "guloso" else 2
        p.append(f'<polyline points="{pontos}" fill="none" stroke="{COR[nome]}" '
                 f'stroke-width="{largura}" stroke-linejoin="round" '
                 f'stroke-linecap="round"/>')
        # rótulo direto em vez de caixa de legenda; duas cores da paleta
        # ficam abaixo de 3:1 na superfície clara e exigem rótulo visível
        yr = y(valores[-1] / total) + 4 + (i - 1.5) * 2
        p.append(f'<text x="{L+larg+10}" y="{yr:.1f}" font-size="12" '
                 f'font-weight="{600 if nome == "guloso" else 400}" '
                 f'fill="{TEXTO if nome == "guloso" else TEXTO_2}">'
                 f'{_escapar(nome)} · {valores[-1]/total:.0%}</text>')
        p.append(f'<circle cx="{L+larg:.1f}" cy="{y(valores[-1]/total):.1f}" r="3.5" '
                 f'fill="{COR[nome]}" stroke="{SURFACE}" stroke-width="2"/>')

    p.append("</svg>")
    return "\n".join(p)


def grafico_ganho(passos, total: int) -> str:
    """Barras: quanto cada unidade nova acrescenta. Deve cair sempre."""
    L, T = 92, 74
    larg, alt = 560, 240
    W, H = L + larg + 40, T + alt + 64
    n = len(passos)
    topo = max(p.ganho for p in passos) / total

    largura_barra = max(larg / n - 2, 1)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="system-ui, -apple-system, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>',
         f'<text x="{L}" y="30" font-size="15" font-weight="600" fill="{TEXTO}">'
         f'Cada unidade nova acrescenta menos que a anterior</text>',
         f'<text x="{L}" y="50" font-size="12" fill="{TEXTO_2}">'
         f'É a submodularidade — a propriedade de onde sai a garantia de 1−1/e</text>']

    for frac in [topo * i / 4 for i in range(5)]:
        yy = T + alt - (frac / topo) * alt
        p.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{L+larg}" y2="{yy:.1f}" '
                 f'stroke="{GRADE}" stroke-width="1"/>')
        p.append(f'<text x="{L-10}" y="{yy+4:.1f}" font-size="11" fill="{TEXTO_2}" '
                 f'text-anchor="end">{frac:.1%}</text>')

    for i, passo in enumerate(passos):
        h = (passo.ganho / total) / topo * alt
        xx = L + i * (larg / n)
        # 2px de folga entre barras, e topo arredondado ancorado na base
        p.append(f'<rect x="{xx:.1f}" y="{T+alt-h:.1f}" width="{largura_barra:.1f}" '
                 f'height="{max(h, 0.5):.1f}" rx="2" fill="{COR["guloso"]}"/>')

    for k in range(10, n + 1, 10):
        xx = L + (k - 0.5) * (larg / n)
        p.append(f'<text x="{xx:.1f}" y="{T+alt+22}" font-size="11" '
                 f'fill="{TEXTO_2}" text-anchor="middle">{k}</text>')
    p.append(f'<text x="{L+larg/2:.0f}" y="{T+alt+46}" font-size="12" '
             f'fill="{TEXTO_2}" text-anchor="middle">ordem de escolha</text>')
    p.append("</svg>")
    return "\n".join(p)


def grafico_mapa(inst: Instancia, escolhidas: list[int]) -> str:
    """
    O mapa do DF: um ponto por setor censitário, azul se coberto.

    A projeção é a mais simples que não distorce: multiplicar a longitude
    pelo cosseno da latitude. Num território de 60 por 96 km a curvatura
    da Terra não aparece, e um mapa de verdade exigiria biblioteca de GIS
    — que o projeto inteiro evita de propósito.

    O ponto é o centroide do setor, e o tamanho vai com a raiz da
    população: a raiz, e não a população, porque o olho lê **área**, e
    área cresce com o quadrado do raio. Com população direta no raio, um
    setor de dez mil habitantes viraria uma bolha vinte vezes maior do
    que é.
    """
    L, T = 24, 78
    larg, alt = 620, 392
    W, H = L + larg + 24, T + alt + 52

    setores, unidades = inst.setores, inst.unidades
    cos_lat = math.cos(math.radians(
        sum(s.lat for s in setores) / len(setores)))

    # o enquadramento sai só dos setores, que não mudam com o `k`. Se as
    # escolhidas entrassem na conta, cada `k` daria um recorte diferente e
    # dois mapas lado a lado deixariam de ser comparáveis — que é
    # justamente para o que eles servem.
    lat_min = min(s.lat for s in setores)
    lat_max = max(s.lat for s in setores)
    lon_min = min(s.lon for s in setores)
    lon_max = max(s.lon for s in setores)

    vao_x = max((lon_max - lon_min) * cos_lat, 1e-9)
    vao_y = max(lat_max - lat_min, 1e-9)
    # a mesma escala nos dois eixos, senão o DF sai esticado
    escala = min(larg / vao_x, alt / vao_y)
    folga_x = (larg - vao_x * escala) / 2
    folga_y = (alt - vao_y * escala) / 2

    def x(lon): return L + folga_x + (lon - lon_min) * cos_lat * escala
    def y(lat): return T + folga_y + (lat_max - lat) * escala

    cobertos = inst.cobertos_por(escolhidas)
    coberta = inst.populacao_de(cobertos)
    total = inst.populacao_total
    maior = max((s.populacao for s in setores), default=1) or 1

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="system-ui, -apple-system, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>',
         f'<text x="{L}" y="30" font-size="15" font-weight="600" fill="{TEXTO}">'
         f'Onde {len(escolhidas)} unidades alcançam '
         + f'{coberta:,}'.replace(",", ".")
         + f' pessoas — {coberta/total:.0%} do DF</text>',
         f'<text x="{L}" y="50" font-size="12" fill="{TEXTO_2}">'
         + f'{len(setores):,}'.replace(",", ".")
         + ' setores censitários · o tamanho do ponto é a população · '
         f'raio de {inst.raio_km:g} km</text>']

    # o alcance de cada escolhida, por baixo de tudo: é ele que explica
    # por que os pontos ficaram azuis
    raio_px = inst.raio_km / KM_POR_GRAU * escala
    for j in escolhidas:
        p.append(f'<circle cx="{x(unidades[j].lon):.1f}" '
                 f'cy="{y(unidades[j].lat):.1f}" r="{raio_px:.1f}" '
                 f'fill="{COR["guloso"]}" fill-opacity="0.07" '
                 f'stroke="{COR["guloso"]}" stroke-opacity="0.25" stroke-width="1"/>')

    # setores sem cobertura primeiro, para o azul ficar por cima
    for coberto in (False, True):
        cor = COR["guloso"] if coberto else SEM_COBERTURA
        for i, s in enumerate(setores):
            if (i in cobertos) is not coberto or s.populacao <= 0:
                continue
            r = 1.0 + 3.0 * math.sqrt(s.populacao / maior)
            p.append(f'<circle cx="{x(s.lon):.1f}" cy="{y(s.lat):.1f}" '
                     f'r="{r:.1f}" fill="{cor}"/>')

    # as escolhidas por cima, com anel da própria superfície para não
    # sumirem dentro da nuvem de pontos
    for j in escolhidas:
        p.append(f'<circle cx="{x(unidades[j].lon):.1f}" '
                 f'cy="{y(unidades[j].lat):.1f}" r="4" fill="{TEXTO}" '
                 f'stroke="{SURFACE}" stroke-width="2"/>')

    rotulos = [(COR["guloso"], "setor coberto", TEXTO),
               (SEM_COBERTURA, "setor sem cobertura", TEXTO_2),
               (TEXTO, "unidade escolhida", TEXTO)]
    xr = L
    for cor, texto, cor_texto in rotulos:
        p.append(f'<circle cx="{xr+5}" cy="{T+alt+26}" r="4.5" fill="{cor}" '
                 f'stroke="{SURFACE}" stroke-width="1.5"/>')
        p.append(f'<text x="{xr+16}" y="{T+alt+30}" font-size="12" '
                 f'fill="{cor_texto}">{_escapar(texto)}</text>')
        xr += 22 + len(texto) * 6.6
    p.append("</svg>")
    return "\n".join(p)


def tabela(series: dict[str, list[int]], total: int,
           comparacoes: list[Comparacao], marcos: list[int]) -> str:
    linhas = ["## Guloso contra as escolhas óbvias", "",
              "| unidades | " + " | ".join(
                  f"**{n}**" if n == "guloso" else n
                  for n in sorted(series, key=lambda n: -series[n][-1])) + " |",
              "| --- |" + " --- |" * len(series)]
    ordem = sorted(series, key=lambda n: -series[n][-1])
    for k in marcos:
        if k > len(series["guloso"]):
            continue
        celulas = " | ".join(f"{series[n][k-1]/total:.1%}" for n in ordem)
        linhas.append(f"| {k} | {celulas} |")

    melhor_base = max((n for n in series if n != "guloso"),
                      key=lambda n: series[n][-1])
    k = marcos[len(marcos) // 2]
    vantagem = series["guloso"][k-1] / series[melhor_base][k-1]
    linhas += ["", f"Com {k} unidades o guloso cobre **{vantagem:.2f}×** o que a "
                   f"melhor linha de base alcança.", ""]

    linhas += ["## Guloso contra o ótimo", "",
               "| candidatos | k | guloso | ótimo | razão |", "| --- | --- | --- | --- | --- |"]
    for c in comparacoes:
        linhas.append(f"| {c.candidatos} | {c.k} | {c.guloso:,} | {c.otimo:,} | "
                      f"{c.razao:.2%} |".replace(",", "."))
    razoes = [c.razao for c in comparacoes]
    acertos = sum(1 for r in razoes if r > 0.9999)
    linhas += ["",
               f"Encontrou o ótimo em **{acertos} de {len(razoes)}** instâncias. "
               f"Pior caso **{min(razoes):.2%}**, média **{sum(razoes)/len(razoes):.2%}** — "
               f"contra uma garantia teórica de apenas **63,21%**.", ""]
    return "\n".join(linhas)


def _desenhar_mapa(inst: Instancia, base: Path, k: int) -> int:
    """
    Grava o mapa de `k` unidades e devolve o código de saída.

    O nome do arquivo leva o `k` justamente para `--so-mapa` poder ser
    chamado várias vezes sem uma rodada apagar a anterior: k = 5, 20 e 60
    lado a lado mostram o azul se espalhando.
    """
    escolhidas = guloso(inst, k)
    destino = base.with_name(f"{base.name}_mapa_k{k}.svg")
    destino.write_text(grafico_mapa(inst, escolhidas), encoding="utf-8")

    coberta = inst.populacao_de(inst.cobertos_por(escolhidas))
    total = inst.populacao_total
    print(f"{k} unidades alcançam {coberta:,} pessoas ({coberta/total:.1%})"
          .replace(",", "."))
    print(f"gravado em {destino}")
    return 0


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("--raio", type=float, default=2.0, help="raio de cobertura em km")
    ap.add_argument("--kmax", type=int, default=60, help="até quantas unidades")
    ap.add_argument("--instancias", type=int, default=12,
                    help="quantas instâncias reduzidas comparar com o ótimo")
    ap.add_argument("--kmapa", type=int, default=20,
                    help="quantas unidades desenhar no mapa")
    ap.add_argument("--so-mapa", action="store_true",
                    help="desenha só o mapa e sai (segundos, em vez de minutos)")
    args = ap.parse_args(argv)

    from src.cobertura import carregar
    try:
        inst = carregar(args.raio)
    except FileNotFoundError as erro:
        print(f"não encontrei {erro} — veja data/README.md", file=sys.stderr)
        return 1
    except ImportError as erro:
        print(erro, file=sys.stderr)
        return 1

    total = inst.populacao_total
    print(f"raio de {args.raio:g} km · {len(inst.unidades)} unidades · "
          f"{len(inst.setores)} setores")

    SAIDA.mkdir(exist_ok=True)
    base = SAIDA / f"validacao_raio{args.raio:g}"

    if args.so_mapa:
        return _desenhar_mapa(inst, base, args.kmapa)

    print("calculando a curva de cobertura...")
    series = curva(inst, args.kmax)
    print("comparando com o ótimo...")
    comparacoes = contra_o_otimo(inst, args.instancias)
    passos = historico(inst, args.kmax)

    (base.with_name(base.name + "_cobertura.svg")).write_text(
        grafico_curva(series, total, args.raio), encoding="utf-8")
    (base.with_name(base.name + "_ganho.svg")).write_text(
        grafico_ganho(passos, total), encoding="utf-8")
    _desenhar_mapa(inst, base, args.kmapa)

    marcos = [k for k in (5, 10, 20, 40, 60) if k <= args.kmax]
    md = tabela(series, total, comparacoes, marcos)
    base.with_suffix(".md").write_text(md, encoding="utf-8")
    base.with_suffix(".json").write_text(json.dumps({
        "raio_km": args.raio,
        "populacao_total": total,
        "populacao_alcancavel": inst.populacao_alcancavel,
        "series": series,
        "ganho_marginal": [p.ganho for p in passos],
        "contra_o_otimo": [vars(c) | {"razao": c.razao} for c in comparacoes],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(md)
    print(f"gravado em {base}_cobertura.svg, _ganho.svg, .md e .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
