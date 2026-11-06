"""Painel da loja (Streamlit).
Rode na raiz do projeto, com o .venv ativo:   streamlit run dashboards/app.py"""
import sys
from datetime import timedelta
from pathlib import Path

# permite "from dashboards import dados" mesmo quando o Streamlit roda este arquivo direto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from dashboards import dados

st.set_page_config(page_title="Painel da Loja", page_icon="📊", layout="wide")


def brl(valor: float) -> str:
    """1234.5 -> 'R$ 1.234,50'"""
    return f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


@st.cache_data(ttl=60)
def carregar():
    return dados.carregar_vendas(), dados.carregar_estoque()


# ------------------------------------------------------------------ dados
if not dados.BANCO.exists():
    st.error("Banco `loja.db` não encontrado. Rode antes, na raiz do projeto: `python -m src.pipeline`")
    st.stop()

vendas, estoque = carregar()
if vendas.empty:
    st.title("📊 Painel da Loja")
    st.info("Ainda não há vendas registradas. Assim que a primeira venda entrar na planilha e o pipeline "
            "rodar, os indicadores aparecem aqui.")
    if estoque.empty:
        st.caption("O cadastro de produtos também está vazio.")
    else:
        st.subheader("Estoque atual")
        st.dataframe(estoque.rename(columns={"produto": "Produto", "categoria": "Categoria",
                                             "estoque_atual": "Estoque"}).drop(columns="sku"),
                     hide_index=True)
    st.stop()

# ------------------------------------------------------------------ filtros
st.sidebar.header("Filtros")
data_min = vendas["data"].min().date()
data_max = vendas["data"].max().date()
inicio_padrao = max(data_min, data_max - timedelta(days=29))

periodo = st.sidebar.date_input(
    "Período", value=(inicio_padrao, data_max),
    min_value=data_min, max_value=data_max, format="DD/MM/YYYY")
if not (isinstance(periodo, tuple) and len(periodo) == 2):
    st.info("Escolha a data inicial e a final no filtro de período.")
    st.stop()
inicio, fim = periodo

todas_categorias = sorted(vendas["categoria"].unique())
categorias = st.sidebar.multiselect("Categorias", todas_categorias, default=todas_categorias)
frequencia = st.sidebar.radio("Agrupar por", list(dados.FREQUENCIAS), index=1, horizontal=True)

if st.sidebar.button("Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

# ------------------------------------------------------------------ cabeçalho e KPIs
st.title("📊 Painel da Loja")
st.caption(f"Dados de {data_min:%d/%m/%Y} a {data_max:%d/%m/%Y}. "
           "Os números são de lucro bruto (receita menos custo do produto).")

v = dados.filtrar(vendas, inicio, fim, categorias)
if v.empty:
    st.warning("Nenhuma venda no período e nas categorias escolhidos.")
    st.stop()

atual = dados.kpis(v)
anterior = dados.kpis(dados.periodo_anterior(vendas, inicio, fim, categorias))


def delta(chave: str):
    var = dados.variacao(atual[chave], anterior[chave])
    return None if var is None else f"{var:+.1f}%"


c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Faturamento", brl(atual["faturamento"]), delta("faturamento"))
c2.metric("Lucro bruto", brl(atual["lucro"]), delta("lucro"))
c3.metric("Margem", f"{atual['margem']:.1f}%",
          f"{atual['margem'] - anterior['margem']:+.1f} p.p." if anterior["faturamento"] else None)
c4.metric("Vendas", atual["vendas"], delta("vendas"))
c5.metric("Ticket médio", brl(atual["ticket"]), delta("ticket"))
st.caption("As variações comparam com o período anterior de mesmo tamanho.")

aba_geral, aba_produtos, aba_estoque, aba_pagamentos = st.tabs(
    ["Visão geral", "Produtos", "Estoque", "Pagamentos e equipe"])

# ------------------------------------------------------------------ visão geral
with aba_geral:
    esquerda, direita = st.columns([2, 1])
    with esquerda:
        st.subheader(f"Evolução por {frequencia.lower()}")
        serie = dados.serie_temporal(v, frequencia, inicio, fim)
        if frequencia == "Dia":
            st.line_chart(serie[["Faturamento", "Média móvel 7 dias"]])
            st.caption("Dias sem venda aparecem com zero. A média móvel suaviza a oscilação.")
        else:
            st.bar_chart(serie[["Faturamento", "Lucro bruto"]])
            if frequencia == "Semana":
                st.caption("A semana começa na segunda-feira; a primeira e a última podem estar incompletas.")
    with direita:
        st.subheader("Por dia da semana")
        nomes = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        por_dia = (v.assign(d=v["data"].dt.dayofweek).groupby("d")["valor_total"].sum()
                   .reindex(range(7), fill_value=0.0))
        por_dia.index = nomes
        st.bar_chart(por_dia)

# ------------------------------------------------------------------ produtos
with aba_produtos:
    cat = dados.por_categoria(v)
    esquerda, direita = st.columns(2)
    with esquerda:
        st.subheader("Faturamento por categoria")
        st.bar_chart(cat.set_index("categoria")["faturamento"])
    with direita:
        st.subheader("Margem por categoria")
        st.dataframe(
            cat.rename(columns={"categoria": "Categoria", "unidades": "Unidades",
                                "faturamento": "Faturamento", "lucro": "Lucro bruto",
                                "margem_pct": "Margem %"}),
            hide_index=True,
            column_config={"Faturamento": st.column_config.NumberColumn(format="R$ %.2f"),
                           "Lucro bruto": st.column_config.NumberColumn(format="R$ %.2f"),
                           "Margem %": st.column_config.NumberColumn(format="%.1f%%")})

    st.subheader("10 produtos que mais faturam")
    top = dados.top_produtos(v, 10)
    st.dataframe(
        top.rename(columns={"produto": "Produto", "categoria": "Categoria", "unidades": "Unidades",
                            "faturamento": "Faturamento", "lucro": "Lucro bruto", "margem_pct": "Margem %"}),
        hide_index=True,
        column_config={
            "Faturamento": st.column_config.ProgressColumn(
                format="R$ %.2f", min_value=0, max_value=float(top["faturamento"].max())),
            "Lucro bruto": st.column_config.NumberColumn(format="R$ %.2f"),
            "Margem %": st.column_config.NumberColumn(format="%.1f%%")})

    with st.expander("Curva ABC (A = primeiros 80% do faturamento, B = até 95%, C = o resto)"):
        abc = dados.curva_abc(v)
        resumo = abc.groupby("classe").agg(produtos=("sku", "count"),
                                           pct_do_faturamento=("pct_individual", "sum")).round(1)
        st.dataframe(resumo.reset_index().rename(columns={
            "classe": "Classe", "produtos": "Produtos", "pct_do_faturamento": "% do faturamento"}),
            hide_index=True)
        st.dataframe(abc.rename(columns={
            "sku": "SKU", "produto": "Produto", "categoria": "Categoria", "faturamento": "Faturamento",
            "pct_individual": "% individual", "pct_acumulado": "% acumulado", "classe": "Classe"}),
            hide_index=True,
            column_config={"Faturamento": st.column_config.NumberColumn(format="R$ %.2f")})

# ------------------------------------------------------------------ estoque
with aba_estoque:
    st.caption("O estoque mostra a situação atual e não depende do filtro de período. "
               "A venda média usa os últimos 30 dias até a última venda registrada.")
    f1, f2 = st.columns(2)
    limite_baixo = f1.slider("Alerta de estoque baixo: até (unidades)", 0, 20, 3)
    dias_parado = f2.slider("Produto parado: sem venda há mais de (dias)", 7, 90, 30)

    est = dados.estoque_com_cobertura(estoque, vendas)
    baixo = est[est["estoque_atual"] <= limite_baixo].sort_values("estoque_atual")
    parados = est[(est["estoque_atual"] > 0)
                  & ((est["dias_sem_vender"] > dias_parado) | est["dias_sem_vender"].isna())
                  ].sort_values("dias_sem_vender", ascending=False)

    m1, m2, m3 = st.columns(3)
    m1.metric("Produtos cadastrados", len(est))
    m2.metric("Com estoque baixo", len(baixo))
    m3.metric("Parados", len(parados))

    colunas = {"produto": "Produto", "categoria": "Categoria", "estoque_atual": "Estoque",
               "venda_diaria": "Venda/dia", "dias_cobertura": "Cobertura (dias)",
               "dias_sem_vender": "Dias sem vender"}
    st.subheader("Estoque baixo")
    st.dataframe(baixo[list(colunas)].rename(columns=colunas), hide_index=True)
    st.subheader("Produtos parados")
    st.dataframe(parados[list(colunas)].rename(columns=colunas), hide_index=True)
    with st.expander("Estoque completo"):
        st.dataframe(est.sort_values("estoque_atual")[list(colunas)].rename(columns=colunas),
                     hide_index=True)

# ------------------------------------------------------------------ pagamentos e equipe
with aba_pagamentos:
    esquerda, direita = st.columns(2)
    with esquerda:
        st.subheader("Forma de pagamento")
        pag = dados.por_pagamento(v)
        st.bar_chart(pag.set_index("forma_pagamento")["faturamento"])
        st.dataframe(
            pag.rename(columns={"forma_pagamento": "Forma", "vendas": "Vendas",
                                "faturamento": "Faturamento", "pct_faturamento": "% do faturamento"}),
            hide_index=True,
            column_config={"Faturamento": st.column_config.NumberColumn(format="R$ %.2f")})
    with direita:
        st.subheader("Vendedores")
        vend = dados.por_vendedor(v)
        st.bar_chart(vend.set_index("vendedor")["faturamento"])
        st.dataframe(
            vend.rename(columns={"vendedor": "Vendedor", "vendas": "Vendas",
                                 "faturamento": "Faturamento", "ticket_medio": "Ticket médio"}),
            hide_index=True,
            column_config={"Faturamento": st.column_config.NumberColumn(format="R$ %.2f"),
                           "Ticket médio": st.column_config.NumberColumn(format="R$ %.2f")})
