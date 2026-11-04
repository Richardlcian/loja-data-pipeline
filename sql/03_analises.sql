-- =====================================================================
-- Consultas de análise da loja (SQLite)
-- Cada consulta começa com "-- ## N. título" (o rodar_consulta.py usa isso).
-- "Hoje" = data da última venda registrada, assim as análises funcionam
-- mesmo com dados fictícios antigos.
-- =====================================================================

-- ## 1. Resumo mensal: vendas, faturamento, lucro, margem e ticket médio
SELECT t.ano,
       t.mes,
       COUNT(DISTINCT f.id_venda)                                        AS qtd_vendas,
       ROUND(SUM(f.valor_total), 2)                                      AS faturamento,
       ROUND(SUM(f.valor_total - f.custo_total), 2)                      AS lucro_bruto,
       ROUND(100.0 * SUM(f.valor_total - f.custo_total) / SUM(f.valor_total), 1) AS margem_pct,
       ROUND(SUM(f.valor_total) * 1.0 / COUNT(DISTINCT f.id_venda), 2)   AS ticket_medio
FROM fato_vendas f
JOIN dim_tempo t USING (data)
GROUP BY t.ano, t.mes
ORDER BY t.ano, t.mes;

-- ## 2. Faturamento e margem por categoria
SELECT p.categoria,
       SUM(f.quantidade)                                                 AS unidades,
       ROUND(SUM(f.valor_total), 2)                                      AS faturamento,
       ROUND(SUM(f.valor_total - f.custo_total), 2)                      AS lucro_bruto,
       ROUND(100.0 * SUM(f.valor_total - f.custo_total) / SUM(f.valor_total), 1) AS margem_pct,
       ROUND(100.0 * SUM(f.valor_total) / (SELECT SUM(valor_total) FROM fato_vendas), 1) AS pct_do_faturamento
FROM fato_vendas f
JOIN dim_produto p USING (id_produto)
GROUP BY p.categoria
ORDER BY faturamento DESC;

-- ## 3. Top 10 produtos dos últimos 30 dias (por unidades vendidas)
WITH ref AS (SELECT MAX(data) AS hoje FROM fato_vendas)
SELECT p.nome,
       p.categoria,
       SUM(f.quantidade)            AS unidades,
       ROUND(SUM(f.valor_total), 2) AS receita
FROM fato_vendas f
JOIN dim_produto p USING (id_produto)
WHERE f.data > date((SELECT hoje FROM ref), '-30 day')
GROUP BY p.nome, p.categoria
ORDER BY unidades DESC, receita DESC
LIMIT 10;

-- ## 4. Produtos parados: com estoque e sem venda há mais de 30 dias
WITH ref AS (SELECT MAX(data) AS hoje FROM fato_vendas)
SELECT e.sku,
       e.nome,
       e.categoria,
       e.estoque_atual,
       MAX(f.data) AS ultima_venda,
       CAST(julianday((SELECT hoje FROM ref)) - julianday(MAX(f.data)) AS INTEGER) AS dias_sem_vender
FROM vw_estoque_atual e
JOIN dim_produto p ON p.sku = e.sku
LEFT JOIN fato_vendas f ON f.id_produto = p.id_produto
GROUP BY e.sku, e.nome, e.categoria, e.estoque_atual
HAVING e.estoque_atual > 0
   AND (MAX(f.data) IS NULL
        OR MAX(f.data) <= date((SELECT hoje FROM ref), '-30 day'))
ORDER BY dias_sem_vender DESC;

-- ## 5. Cobertura de estoque em dias (com base na venda média dos últimos 30 dias)
WITH ref AS (SELECT MAX(data) AS hoje FROM fato_vendas),
media AS (
    SELECT id_produto, SUM(quantidade) / 30.0 AS venda_diaria
    FROM fato_vendas
    WHERE data > date((SELECT hoje FROM ref), '-30 day')
    GROUP BY id_produto
)
SELECT p.nome,
       e.estoque_atual,
       ROUND(m.venda_diaria, 2)                                AS venda_diaria,
       ROUND(e.estoque_atual / NULLIF(m.venda_diaria, 0), 1)   AS dias_de_cobertura
FROM vw_estoque_atual e
JOIN dim_produto p ON p.sku = e.sku
LEFT JOIN media m ON m.id_produto = p.id_produto
ORDER BY dias_de_cobertura IS NULL, dias_de_cobertura;

-- ## 6. Vendas por dia da semana
SELECT t.nome_dia,
       COUNT(DISTINCT f.id_venda)   AS qtd_vendas,
       ROUND(SUM(f.valor_total), 2) AS faturamento
FROM fato_vendas f
JOIN dim_tempo t USING (data)
GROUP BY t.dia_semana, t.nome_dia
ORDER BY t.dia_semana;

-- ## 7. Participação por forma de pagamento
SELECT forma_pagamento,
       COUNT(DISTINCT id_venda)  AS qtd_vendas,
       ROUND(SUM(valor_total), 2) AS faturamento,
       ROUND(100.0 * SUM(valor_total) / (SELECT SUM(valor_total) FROM fato_vendas), 1) AS pct_faturamento
FROM fato_vendas
GROUP BY forma_pagamento
ORDER BY faturamento DESC;

-- ## 8. Desempenho por vendedor
SELECT COALESCE(v.nome, '(sem vendedor)')                                  AS vendedor,
       COUNT(DISTINCT f.id_venda)                                          AS qtd_vendas,
       ROUND(SUM(f.valor_total), 2)                                        AS faturamento,
       ROUND(SUM(f.valor_total) * 1.0 / COUNT(DISTINCT f.id_venda), 2)     AS ticket_medio
FROM fato_vendas f
LEFT JOIN dim_vendedor v USING (id_vendedor)
GROUP BY vendedor
ORDER BY faturamento DESC;

-- ## 9. Evolução semanal com variação sobre a semana anterior (função de janela LAG)
WITH semanal AS (
    SELECT strftime('%Y-W%W', data) AS semana,
           MIN(data)                AS primeiro_dia,
           SUM(valor_total)         AS faturamento
    FROM fato_vendas
    GROUP BY semana
)
SELECT semana,
       primeiro_dia,
       ROUND(faturamento, 2)                                   AS faturamento,
       ROUND(LAG(faturamento) OVER (ORDER BY semana), 2)       AS semana_anterior,
       ROUND(100.0 * (faturamento - LAG(faturamento) OVER (ORDER BY semana))
             / LAG(faturamento) OVER (ORDER BY semana), 1)     AS variacao_pct
FROM semanal
ORDER BY semana;

-- ## 10. Média móvel de 7 dias de venda (suaviza a oscilação de poucas vendas por dia)
SELECT data,
       ROUND(faturamento, 2) AS faturamento,
       ROUND(AVG(faturamento) OVER (
           ORDER BY data ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS media_movel_7d
FROM vw_vendas_diarias
ORDER BY data;

-- ## 11. Ranking de produtos dentro de cada categoria (RANK com PARTITION BY)
WITH produto_receita AS (
    SELECT p.categoria, p.nome,
           SUM(f.valor_total) AS receita,
           SUM(f.quantidade)  AS unidades
    FROM fato_vendas f
    JOIN dim_produto p USING (id_produto)
    GROUP BY p.categoria, p.nome
)
SELECT categoria,
       nome,
       ROUND(receita, 2) AS receita,
       unidades,
       RANK() OVER (PARTITION BY categoria ORDER BY receita DESC) AS posicao
FROM produto_receita
ORDER BY categoria, posicao;

-- ## 12. Curva ABC: A = produtos que somam os primeiros 80% do faturamento, B = até 95%, C = o resto
WITH receita AS (
    SELECT p.sku, p.nome, p.categoria, SUM(f.valor_total) AS receita
    FROM fato_vendas f
    JOIN dim_produto p USING (id_produto)
    GROUP BY p.sku, p.nome, p.categoria
),
acumulado AS (
    SELECT *,
           100.0 * SUM(receita) OVER (ORDER BY receita DESC
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                 / SUM(receita) OVER ()                                  AS pct_acumulado,
           100.0 * receita / SUM(receita) OVER ()                        AS pct_individual
    FROM receita
)
SELECT sku,
       nome,
       categoria,
       ROUND(receita, 2)        AS receita,
       ROUND(pct_acumulado, 1)  AS pct_acumulado,
       CASE WHEN pct_acumulado - pct_individual < 80 THEN 'A'
            WHEN pct_acumulado - pct_individual < 95 THEN 'B'
            ELSE 'C' END        AS classe
FROM acumulado
ORDER BY receita DESC;

-- ## 13. Impacto dos descontos por categoria
SELECT p.categoria,
       COUNT(*)                                                         AS itens,
       SUM(f.desconto > 0)                                              AS itens_com_desconto,
       ROUND(100.0 * SUM(f.desconto > 0) / COUNT(*), 1)                 AS pct_itens_com_desconto,
       ROUND(SUM(f.desconto), 2)                                        AS total_descontos,
       ROUND(100.0 * SUM(f.desconto) / SUM(f.valor_total + f.desconto), 1) AS pct_desconto_sobre_bruto
FROM fato_vendas f
JOIN dim_produto p USING (id_produto)
GROUP BY p.categoria
ORDER BY total_descontos DESC;

-- ## 14. Produtos que mais geram lucro bruto (e sua margem)
SELECT p.nome,
       p.categoria,
       SUM(f.quantidade)                                                 AS unidades,
       ROUND(SUM(f.valor_total - f.custo_total), 2)                      AS lucro_bruto,
       ROUND(100.0 * SUM(f.valor_total - f.custo_total) / SUM(f.valor_total), 1) AS margem_pct
FROM fato_vendas f
JOIN dim_produto p USING (id_produto)
GROUP BY p.nome, p.categoria
ORDER BY lucro_bruto DESC
LIMIT 10;
