from __future__ import annotations
 
import random
 
import pandas as pd
import streamlit as st
 
from src.cobertura import Instancia, carregar
from src.dados import ARQUIVO_SETORES, ARQUIVO_UBS
from src.exato import exato
from src.guloso import PassoGuloso, historico
from src.linhas_base import LINHAS_DE_BASE, media_aleatoria
from src.mochila import custo_simulado, guloso_mochila, otimo_mochila, valor_local
 
st.set_page_config(page_title="Cobertura de Saúde no DF", page_icon="🏥", layout="wide")

LIMITE_AMOSTRA_EXATA = 15
 
 
def _tem_pyshp() -> bool:
    try:
        import shapefile  # noqa: F401
    except ImportError:
        return False
    return True
 
 
def _dados_disponiveis() -> bool:
    return (ARQUIVO_UBS.exists()
            and ARQUIVO_SETORES.with_suffix(".shp").exists()
            and _tem_pyshp())
 
 
def mostrar_instrucoes_de_dados() -> None:
    st.error("Dados brutos não encontrados em `data/raw/`.")
    st.markdown(
        "Baixe os dois arquivos conforme o README e coloque em "
        "`data/raw/`:\n\n"
        "- **UBS** (CNES): "
        "[dadosabertos.saude.gov.br](https://dadosabertos.saude.gov.br/"
        "dataset/unidades-basicas-de-saude-ubs)\n"
        "- **Setores censitários** (IBGE): "
        "[ftp.ibge.gov.br](https://ftp.ibge.gov.br/Censos/"
        "Censo_Demografico_2022/Agregados_por_Setores_Censitarios/"
        "malha_com_atributos/setores/shp/UF/DF/DF_setores_CD2022.zip)\n\n"
        "Depois `pip install -r requirements.txt` para o `pyshp`."
    )
 
 
@st.cache_data(show_spinner="Carregando UBS e setores censitários…")
def carregar_instancia(raio_km: float) -> Instancia:
    return carregar(raio_km)
 
 
def _formatar(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")
 
 
def mostrar_metricas_da_instancia(inst: Instancia) -> None:
    total = inst.populacao_total
    alcancavel = inst.populacao_alcancavel
    col1, col2, col3 = st.columns(3)
    col1.metric("População do DF", _formatar(total))
    col2.metric(
        "Alcançável com este raio", _formatar(alcancavel),
        f"{alcancavel / total:.1%} do total",
    )
    col3.metric("Fora de qualquer alcance", _formatar(total - alcancavel))
 
 
def mostrar_resultado_guloso(inst: Instancia, passos: list[PassoGuloso]) -> None:
    total = inst.populacao_total
    coberta = passos[-1].acumulado if passos else 0
 
    st.subheader("Resultado do guloso")
    col1, col2 = st.columns(2)
    col1.metric("Unidades escolhidas", f"{len(passos)}")
    col2.metric("População coberta", _formatar(coberta), f"{coberta / total:.1%} do DF")
 
    if not passos:
        st.info("Nenhuma unidade escolhida — aumente k.")
        return
 
    linhas = []
    for i, passo in enumerate(passos, 1):
        unidade = inst.unidades[passo.unidade]
        linhas.append({
            "#": i,
            "Unidade": unidade.nome,
            "Bairro": unidade.bairro,
            "Ganho marginal": passo.ganho,
            "Acumulado": passo.acumulado,
        })
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
 
    st.caption(
        "Ganho marginal de cada escolha — a razão de ser do guloso é o "
        "degrau decrescente abaixo: cada unidade nova soma menos gente "
        "do que a anterior, porque o que ela cobre vai sobrando cada vez "
        "menos."
    )
    st.bar_chart(
        pd.DataFrame({"Ganho marginal": [p.ganho for p in passos]},
                     index=pd.Index(range(1, len(passos) + 1),
                                    name="ordem de escolha")),
    )
 
 
def mostrar_mapa(inst: Instancia, escolhidas: list[int]) -> None:
    import pydeck as pdk
 
    cobertos = inst.cobertos_por(escolhidas)
 
    setores_df = pd.DataFrame([
        {"lat": s.lat, "lon": s.lon, "populacao": s.populacao,
         "cor": [30, 140, 90, 140] if i in cobertos else [170, 170, 170, 80]}
        for i, s in enumerate(inst.setores)
    ])
    unidades_df = pd.DataFrame([
        {"lat": inst.unidades[j].lat, "lon": inst.unidades[j].lon,
         "nome": inst.unidades[j].nome}
        for j in escolhidas
    ])
 
    camada_setores = pdk.Layer(
        "ScatterplotLayer", data=setores_df,
        get_position="[lon, lat]", get_fill_color="cor",
        get_radius=180, pickable=False,
    )
    camada_unidades = pdk.Layer(
        "ScatterplotLayer", data=unidades_df,
        get_position="[lon, lat]", get_fill_color=[200, 30, 30, 230],
        get_radius=350, pickable=True,
    )
 
    centro_lat = sum(s.lat for s in inst.setores) / len(inst.setores)
    centro_lon = sum(s.lon for s in inst.setores) / len(inst.setores)
 
    st.pydeck_chart(pdk.Deck(
        layers=[camada_setores, camada_unidades],
        initial_view_state=pdk.ViewState(
            latitude=centro_lat, longitude=centro_lon, zoom=9.5,
        ),
        tooltip={"text": "{nome}"},
    ))
    st.caption(
        "🟢 setor coberto · ⚪ setor fora de alcance · 🔴 unidade escolhida"
    )
 
 
def mostrar_comparacao_linhas_de_base(inst: Instancia, k: int, coberta_guloso: int) -> None:
    total = inst.populacao_total
 
    st.subheader("Guloso vs. as escolhas óbvias")
    st.caption(
        "O guloso só vale a pena se bater quem escolheria sem algoritmo "
        "nenhum: as unidades que cobrem mais gente sozinhas, as mais "
        "centrais, ou um sorteio."
    )
 
    linhas = [{"Estratégia": "Guloso", "População coberta": coberta_guloso,
               "% do DF": coberta_guloso / total}]
    for nome, escolher in LINHAS_DE_BASE.items():
        if nome == "aleatórias":
            coberta = media_aleatoria(inst, k)
            nome = "aleatórias (média de 30)"
        else:
            coberta = inst.populacao_de(inst.cobertos_por(escolher(inst, k)))
        linhas.append({"Estratégia": nome, "População coberta": round(coberta),
                        "% do DF": coberta / total})
 
    df = pd.DataFrame(linhas).sort_values("População coberta", ascending=False)
    st.dataframe(
        df.style.format({"População coberta": "{:,.0f}", "% do DF": "{:.1%}"}),
        hide_index=True, use_container_width=True,
    )
 
 
def mostrar_comparacao_com_otimo(inst: Instancia, k: int) -> None:
    st.subheader("Comparar com o ótimo")
    st.caption(
        f"Busca exaustiva não roda sobre as {len(inst.unidades)} unidades "
        "reais — o número de combinações explode (C(200, 8) já passa de "
        "160 trilhões). Esta seção roda guloso e ótimo lado a lado numa "
        f"**amostra aleatória de até {LIMITE_AMOSTRA_EXATA} unidades**, só "
        "para validar experimentalmente a garantia teórica do guloso "
        "(pelo menos 1 − 1/e ≈ 63,2% do ótimo)."
    )
 
    n_amostra = st.slider(
        "Tamanho da amostra", min_value=5,
        max_value=min(LIMITE_AMOSTRA_EXATA, len(inst.unidades)), value=12,
    )
    semente = st.number_input("Semente do sorteio", value=42, step=1)
 
    sorteio = random.Random(semente)
    indices = sorteio.sample(range(len(inst.unidades)), n_amostra)
    sub_unidades = [inst.unidades[i] for i in indices]
    sub_coberturas = [inst.coberturas[i] for i in indices]
 
    from src.cobertura import Instancia as InstanciaCls
    sub_inst = InstanciaCls(unidades=sub_unidades, setores=inst.setores,
                             coberturas=sub_coberturas, raio_km=inst.raio_km)
 
    k_amostra = min(k, n_amostra)
    passos_guloso = historico(sub_inst, k_amostra)
    coberta_guloso = passos_guloso[-1].acumulado if passos_guloso else 0
    coberta_otima = sub_inst.populacao_de(
        sub_inst.cobertos_por(exato(sub_inst, k_amostra))
    )
 
    col1, col2, col3 = st.columns(3)
    col1.metric("Guloso (amostra)", _formatar(coberta_guloso))
    col2.metric("Ótimo (amostra)", _formatar(coberta_otima))
    razao = coberta_guloso / coberta_otima if coberta_otima else 1.0
    col3.metric("Razão guloso / ótimo", f"{razao:.1%}",
                help="A garantia teórica é só o piso (≥ 63,2%); na prática "
                     "costuma ficar bem mais perto de 100%.")
 
 
#: Acima disso, a DP de otimo_mochila (O(n × orçamento)) fica cara demais
#: para rodar a cada interação do slider.
LIMITE_ORCAMENTO_EXATO = 2_000_000
 
 
def mostrar_mochila(inst: Instancia) -> None:
    """
    Extensão: orçamento em R$ em vez de nº de unidades — Mochila 0/1.
 
    Fica numa seção à parte, atrás de uma caixa de seleção, porque é uma
    pergunta DIFERENTE da Cobertura Máxima acima: aqui o "valor" de cada
    unidade é fixo (população do setor mais próximo), não a cobertura com
    raio que se sobrepõe. Ver docstring de src/mochila.py.
    """
    st.subheader("Extensão: orçamento em R$ (Mochila)")
    st.caption(
        "E se cada unidade custasse um valor diferente para manter, e o "
        "orçamento fosse em reais, não em número de unidades? Vira "
        "Mochila 0/1 — uma pergunta diferente da Cobertura Máxima acima, "
        "com sua própria garantia (≥ 1/2 do ótimo, mais fraca que o "
        "1 − 1/e da Cobertura Máxima, porque falta a submodularidade)."
    )
    st.warning(
        "O CNES não publica custo de manutenção por unidade — o custo "
        "abaixo é **simulado** (ver `src/mochila.py`), não um dado real."
    )
 
    orcamento = st.slider("Orçamento (R$)", min_value=100_000, max_value=5_000_000,
                           value=1_000_000, step=50_000)
 
    custos = custo_simulado(inst)
    valores = valor_local(inst)
    resultado = guloso_mochila(valores, custos, orcamento)
 
    col1, col2, col3 = st.columns(3)
    col1.metric("Unidades escolhidas", f"{len(resultado.escolhidas)}")
    col2.metric("Custo usado", f"R$ {_formatar(resultado.custo_total)}")
    col3.metric("Valor (pop. local somada)", _formatar(resultado.valor_total))
 
    if orcamento <= LIMITE_ORCAMENTO_EXATO:
        otimo = otimo_mochila(valores, custos, orcamento)
        razao = resultado.valor_total / otimo.valor_total if otimo.valor_total else 1.0
        st.caption(
            f"Ótimo (programação dinâmica): {_formatar(otimo.valor_total)} · "
            f"guloso atingiu {razao:.1%} dele "
            "(garantia teórica: ≥ 50%)."
        )
    else:
        st.caption(
            "Ótimo exato não calculado — orçamento grande demais para a "
            "DP rodar interativamente (ver LIMITE_ORCAMENTO_EXATO)."
        )
 
 
def main() -> None:
    st.title("🏥 Cobertura de Saúde no DF")
    st.caption(
        "Com um orçamento de `k` unidades básicas de saúde, quais "
        "escolher para alcançar o maior número de habitantes do DF? "
        "Problema de Cobertura Máxima, resolvido pelo guloso: a cada "
        "passo, a unidade que soma mais gente ainda descoberta."
    )
 
    if not _dados_disponiveis():
        mostrar_instrucoes_de_dados()
        return
 
    with st.sidebar:
        st.header("Parâmetros")
        raio_km = st.slider("Raio de alcance de cada unidade (km)",
                             min_value=0.5, max_value=5.0, value=2.0, step=0.5)
        k = st.slider("Orçamento k (nº de unidades)",
                       min_value=0, max_value=60, value=20)
        comparar_com_otimo = st.checkbox("Comparar com o ótimo (amostra pequena)")
        mostrar_extensao_mochila = st.checkbox("Extensão: orçamento em R$ (Mochila)")
 
    inst = carregar_instancia(raio_km)
    mostrar_metricas_da_instancia(inst)
 
    passos = historico(inst, k)
    escolhidas = [p.unidade for p in passos]
    coberta = passos[-1].acumulado if passos else 0
 
    mostrar_resultado_guloso(inst, passos)
 
    st.subheader("Mapa")
    if escolhidas:
        mostrar_mapa(inst, escolhidas)
    else:
        st.info("Escolha k > 0 para ver o mapa.")
 
    mostrar_comparacao_linhas_de_base(inst, k, coberta)
 
    if comparar_com_otimo:
        mostrar_comparacao_com_otimo(inst, k)
 
    if mostrar_extensao_mochila:
        mostrar_mochila(inst)
 
 
if __name__ == "__main__":
    main()
 