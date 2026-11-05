"""Verificações de qualidade depois da carga. Cada problema vira uma frase de alerta."""
from datetime import date

LIMITE_DIAS_SEM_VENDA = 3      # alerta se a última venda for mais antiga que isso
LIMITE_REJEICAO_PCT = 5.0      # alerta se mais que 5% das linhas de vendas/compras forem rejeitadas


def verificar(con, resumo: dict, verificar_frescor: bool = True, hoje: date | None = None) -> list[str]:
    hoje = hoje or date.today()
    alertas = []

    # 1. linhas rejeitadas na validação
    carregadas = resumo["carregadas"]
    for nome in ("produtos", "vendas", "compras"):
        rejeitadas = len(resumo["rejeitadas"][nome])
        total = rejeitadas + carregadas[nome]
        pct = 100 * rejeitadas / total if total else 0.0
        limite = 0.0 if nome == "produtos" else LIMITE_REJEICAO_PCT   # cadastro: qualquer erro importa
        if rejeitadas and pct > limite:
            alertas.append(f"{rejeitadas} de {total} linhas de '{nome}' foram rejeitadas ({pct:.1f}%). "
                           f"Veja data/processed/rejeitadas_{nome}.csv")

    # 2. dados parados: ninguém registrou venda recentemente
    if verificar_frescor:
        ultima = con.execute("SELECT MAX(data) FROM fato_vendas").fetchone()[0]
        if ultima is None:
            alertas.append("Nenhuma venda carregada no banco.")
        else:
            dias = (hoje - date.fromisoformat(ultima)).days
            if dias > LIMITE_DIAS_SEM_VENDA:
                alertas.append(f"Sem venda registrada há {dias} dias (última em {ultima}). "
                               "A planilha foi preenchida?")

    # 3. estoque negativo: saiu mais do que entrou, então falta registrar uma compra
    negativos = con.execute(
        "SELECT sku, estoque_atual FROM vw_estoque_atual WHERE estoque_atual < 0 ORDER BY estoque_atual").fetchall()
    if negativos:
        lista = ", ".join(f"{sku} ({qtd})" for sku, qtd in negativos[:5])
        alertas.append(f"{len(negativos)} produto(s) com estoque negativo: {lista}. "
                       "Falta registrar uma compra ou a venda está errada.")

    # 4. venda abaixo do custo
    abaixo = con.execute(
        """SELECT f.id_venda, p.sku FROM fato_vendas f JOIN dim_produto p USING (id_produto)
           WHERE f.valor_total < f.custo_total ORDER BY f.data DESC""").fetchall()
    if abaixo:
        lista = ", ".join(f"{v} ({sku})" for v, sku in abaixo[:5])
        alertas.append(f"{len(abaixo)} item(ns) vendido(s) abaixo do custo: {lista}. "
                       "Confira o preço ou o desconto.")

    return alertas
