CREATE VIEW IF NOT EXISTS vw_estoque_atual AS
SELECT
    p.sku,
    p.nome,
    p.categoria,
    COALESCE(c.entradas, 0) - COALESCE(v.saidas, 0) AS estoque_atual
FROM dim_produto p
LEFT JOIN (SELECT id_produto, SUM(quantidade) AS entradas
            FROM fato_compras GROUP BY id_produto) c USING (id_produto)
LEFT JOIN (SELECT id_produto, SUM(quantidade) AS saidas
            FROM fato_vendas GROUP BY id_produto) v USING (id_produto);

CREATE VIEW IF NOT EXISTS vw_vendas_diarias AS
SELECT
    data,
    COUNT(DISTINCT id_venda)    AS qtd_vendas,
    SUM(valor_total)            AS faturamento,
    SUM(valor_total - custo_total)      AS lucro_bruto,
    ROUND(SUM(valor_total) * 1.0 / COUNT(DISTINCT id_venda), 2) AS ticket_medio
FROM fato_vendas
GROUP BY data;