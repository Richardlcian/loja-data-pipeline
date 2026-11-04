# Loja Data Pipeline
Pipeline de dados de vendas e estoque para uma loja de celulares e motos elétricas.

# Modelo de Dados
![Diagrama](image.png)
Granularidade da fato_vendas: uma linha por item vendido.
Chave natural vs. substituta: sku é a chave de negócio; id_produto é a chave substituta.
Idempotência: a restrição UNIQUE (id_venda, id_produto) impede duplicar vendas se o pipeline rodar duas vezes.
Custo na venda: custo_total é gravado no momento da venda, para a margem histórica não mudar quando o custo do produto mudar

Status: em desenvolvimento.