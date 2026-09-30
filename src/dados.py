"""
Carregamento das duas bases: unidades de saúde e setores censitários.

    python -m src.dados

Os arquivos brutos ficam em `data/raw/`, que não é versionado. As
instruções de download estão em `data/README.md`, e rodar este módulo sem
eles imprime os comandos em vez de estourar um traceback.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from src.geometria import centroide

PASTA = Path("data/raw")
ARQUIVO_UBS = PASTA / "Unidades_Basicas_Saude-UBS.csv"
ARQUIVO_SETORES = PASTA / "DF_setores_CD2022"

#: Código do Distrito Federal na tabela de UFs do IBGE.
UF_DF = "53"

#: Caixa que contém o DF, com folga. Serve para pegar coordenada corrompida.
LAT_DF = (-16.10, -15.45)
LON_DF = (-48.35, -47.25)


@dataclass(frozen=True)
class Unidade:
    """Uma unidade básica de saúde."""
    cnes: str
    nome: str
    bairro: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Setor:
    """Um setor censitário, com a população e o centro do seu polígono."""
    codigo: str
    regiao: str
    populacao: int
    lat: float
    lon: float
    urbano: bool


def _numero(texto: str | None) -> float | None:
    """
    Converte um número da base do CNES.

    A LATITUDE vem com ponto decimal e a LONGITUDE com vírgula — não é caso
    isolado, é o arquivo nacional inteiro. Sem trocar a vírgula, todo
    `float()` de longitude estoura.
    """
    if texto is None:
        return None
    texto = texto.strip().replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _no_df(lat: float, lon: float) -> bool:
    return LAT_DF[0] <= lat <= LAT_DF[1] and LON_DF[0] <= lon <= LON_DF[1]


def carregar_unidades(caminho: Path = ARQUIVO_UBS) -> list[Unidade]:
    """
    Unidades do DF com coordenada utilizável.

    Descarta as sem coordenada — 12 das 212, e entre elas há registros que
    nem são UBS ("FISIO SEVEN", "CASA DO MARANHAO"): a base do CNES mistura
    tipos de estabelecimento. Descarta também coordenada fora da caixa do
    DF, que hoje não acontece mas é barato garantir.
    """
    if not caminho.exists():
        raise FileNotFoundError(caminho)

    unidades = []
    with open(caminho, encoding="utf-8", errors="replace") as arquivo:
        for linha in csv.DictReader(arquivo, delimiter=";"):
            if linha["UF"] != UF_DF:
                continue
            lat, lon = _numero(linha["LATITUDE"]), _numero(linha["LONGITUDE"])
            if lat is None or lon is None or not _no_df(lat, lon):
                continue
            unidades.append(Unidade(
                cnes=linha["CNES"].strip(),
                nome=linha["NOME"].strip(),
                bairro=linha["BAIRRO"].strip(),
                lat=lat, lon=lon,
            ))
    return unidades


def carregar_setores(caminho: Path = ARQUIVO_SETORES) -> list[Setor]:
    """
    Setores censitários do DF, cada um reduzido ao centro do seu polígono.

    O shapefile está em SIRGAS 2000 geográfico, ou seja, já em latitude e
    longitude — não há reprojeção a fazer. O `.dbf` traz os atributos junto,
    então a população sai daqui mesmo, sem precisar do CSV nacional.

    `v0001` é a população residente: somada no Brasil inteiro dá
    203.080.756, que é exatamente o total do Censo 2022.
    """
    # importado aqui, e não no topo, para o módulo ser lido sem o pyshp
    try:
        import shapefile
    except ImportError as erro:
        raise ImportError(
            "o pyshp é necessário para ler o shapefile do IBGE: "
            "pip install -r requirements.txt"
        ) from erro

    if not caminho.with_suffix(".shp").exists():
        raise FileNotFoundError(caminho.with_suffix(".shp"))

    leitor = shapefile.Reader(str(caminho))
    campos = [c[0] for c in leitor.fields[1:]]

    setores = []
    for registro, forma in zip(leitor.records(), leitor.shapes()):
        dados = dict(zip(campos, registro))
        lon, lat = centroide(forma.points, list(forma.parts))
        setores.append(Setor(
            codigo=dados["CD_SETOR"],
            regiao=dados["NM_SUBDIST"] or "(sem nome)",
            populacao=int(dados["v0001"] or 0),
            lat=lat, lon=lon,
            urbano=dados["SITUACAO"] == "Urbana",
        ))
    return setores


def _instrucoes() -> str:
    return (
        "Baixe os dois arquivos em data/raw/ (veja data/README.md):\n\n"
        "  UBS      https://dadosabertos.saude.gov.br/dataset/"
        "unidades-basicas-de-saude-ubs\n"
        "  Setores  https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
        "Agregados_por_Setores_Censitarios/malha_com_atributos/setores/shp/UF/DF/"
        "DF_setores_CD2022.zip"
    )


def _main() -> int:
    try:
        unidades = carregar_unidades()
        setores = carregar_setores()
    except FileNotFoundError as erro:
        print(f"não encontrei {erro}\n\n{_instrucoes()}", file=sys.stderr)
        return 1
    except ImportError as erro:
        print(erro, file=sys.stderr)
        return 1

    populacao = sum(s.populacao for s in setores)
    print(f"{len(unidades)} unidades de saúde no DF")
    print(f"{len(setores)} setores censitários · {populacao:,} habitantes"
          .replace(",", "."))
    print(f"{sum(1 for s in setores if not s.urbano)} setores rurais · "
          f"{sum(1 for s in setores if s.populacao == 0)} sem população")

    regioes: dict[str, int] = {}
    for setor in setores:
        regioes[setor.regiao] = regioes.get(setor.regiao, 0) + setor.populacao
    print(f"\n{len(regioes)} regiões administrativas, as cinco maiores:")
    for regiao, pop in sorted(regioes.items(), key=lambda p: -p[1])[:5]:
        print(f"  {regiao:<24} {pop:>9,}".replace(",", "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
