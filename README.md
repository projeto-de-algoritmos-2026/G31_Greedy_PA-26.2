# Cobertura de Saúde no DF

**Número do Grupo:** 31 &nbsp;·&nbsp; **Conteúdo da Disciplina:** Algoritmos Gulosos

Com um orçamento de `k` unidades básicas de saúde, quais escolher para
alcançar o maior número de habitantes do Distrito Federal?

## Alunos

| Matrícula | Aluno |
| --- | --- |
| 222006534 | Anna Clara Cardoso Evangelista Brandão |
| 231026699 | Eduarda Domingos Rodrigues |

## Sobre

*(em construção)*

O problema é o de **Cobertura Máxima**: dado um conjunto de candidatos, cada
um cobrindo um subconjunto da população, escolher `k` deles que cubram o
máximo de pessoas. O algoritmo guloso — a cada passo, pegue quem adiciona
mais gente ainda descoberta — garante pelo menos **1 − 1/e ≈ 63,2%** do ótimo.

Os dados são reais: **200 unidades de saúde** do CNES e **5.418 setores
censitários** do Censo 2022, somando **2.817.381 habitantes**.

## Instalação

Requer **Python 3.10 ou mais novo**. Os comandos rodam da raiz do repositório.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Depois baixe os dados conforme `data/README.md`.

## Uso

```bash
python -m src.dados        # confere o carregamento das duas bases
```

## Testes

```bash
python -m unittest discover
```

Os testes que dependem dos arquivos brutos são pulados quando eles não estão
em `data/raw/`, então a suíte roda num clone recém-feito.

## Apresentação

`<link do vídeo>`

## Referências

- NEMHAUSER, G.; WOLSEY, L.; FISHER, M. *An analysis of approximations for
  maximizing submodular set functions*. Mathematical Programming, 1978.
- CORMEN, T. H. et al. *Introduction to Algorithms*. 3. ed.
