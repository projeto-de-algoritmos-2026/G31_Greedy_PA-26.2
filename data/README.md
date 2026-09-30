# Dados

Nenhum dos arquivos brutos é versionado — `data/raw/` está no `.gitignore`.
Baixe os dois abaixo antes de rodar o projeto. Rodar `python -m src.dados`
sem eles imprime estas mesmas instruções.

## 1. Unidades básicas de saúde — CNES / Ministério da Saúde

<https://dadosabertos.saude.gov.br/dataset/unidades-basicas-de-saude-ubs>

Baixe o CSV e salve como `data/raw/Unidades_Basicas_Saude-UBS.csv`.

| | |
| --- | --- |
| Registros no Brasil | 47.983 |
| No DF (`UF = 53`) | 212 |
| **Com coordenada utilizável** | **200** |

**Atenção ao separador decimal.** A coluna `LATITUDE` usa ponto e a
`LONGITUDE` usa vírgula — no arquivo inteiro, não em linhas isoladas. Um
`float()` direto na longitude estoura. É o que `src.dados._numero` trata.

As 12 unidades descartadas não têm coordenada nenhuma, e entre elas há
registros que sequer são UBS ("FISIO SEVEN", "CASA DO MARANHAO"): a base do
CNES mistura tipos de estabelecimento.

## 2. Setores censitários — Censo 2022 / IBGE

<https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/malha_com_atributos/setores/shp/UF/DF/DF_setores_CD2022.zip>

Descompacte em `data/raw/`, deixando os cinco arquivos (`.shp`, `.dbf`,
`.shx`, `.prj`, `.cpg`) soltos ali.

| | |
| --- | --- |
| Setores no DF | 5.418 |
| População | 2.817.381 |
| Urbanos / rurais | 5.021 / 397 |
| Sem população | 76 |
| Regiões administrativas | 33 |

São só 2,5 MB: é o arquivo do DF, não o nacional. O `.dbf` já traz os 36
atributos junto da geometria, então **não é preciso baixar o CSV nacional
de 102 MB** — a população sai do próprio shapefile.

A coluna de população é a `v0001`. Confirmamos somando-a no Brasil inteiro:
**203.080.756**, exatamente o total do Censo 2022.

O arquivo está em **SIRGAS 2000 geográfico**, ou seja, já em latitude e
longitude. Não há reprojeção a fazer.
