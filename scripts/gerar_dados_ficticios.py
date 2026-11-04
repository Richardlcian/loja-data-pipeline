"""
Gera dados fictícios de uma loja (celulares, motos elétricas, acessórios e perfumes)
nos mesmos formatos das abas da planilha: produtos, vendas e compras.
Volume padrão: ~2 vendas por dia, como o esperado na loja no início.

Uso (na raiz do projeto, com o .venv ativo):
    python scripts/gerar_dados_ficticios.py
    python scripts/gerar_dados_ficticios.py --dias 120 --seed 7
    python scripts/gerar_dados_ficticios.py --com-erros   # injeta linhas inválidas

Saída: data/sample/produtos.csv, vendas.csv e compras.csv
"""
import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

PASTA_SAIDA = Path(__file__).resolve().parent.parent / "data" / "sample"

# Precisam ser idênticas às de config/settings.py (FORMAS_PAGAMENTO)
PAGAMENTOS = ["Pix", "Cartão de débito", "Cartão de crédito", "Dinheiro"]
PESO_PAGAMENTOS = [45, 20, 28, 7]

VENDEDORES = ["Maria", "Carlos", "Ana", "Pedro"]

# (sku, nome, categoria, marca, custo_unitario, preco_tabela)
PRODUTOS = [
    ("CEL-001", "Smartphone Alfa 128GB", "Celular", "Alfa", 900.00, 1499.00),
    ("CEL-002", "Smartphone Alfa 256GB", "Celular", "Alfa", 1250.00, 1999.00),
    ("CEL-003", "Smartphone Beta 64GB", "Celular", "Beta", 600.00, 999.00),
    ("CEL-004", "Smartphone Beta 128GB", "Celular", "Beta", 780.00, 1299.00),
    ("CEL-005", "Smartphone Gama Pro 256GB", "Celular", "Gama", 2200.00, 3299.00),
    ("CEL-006", "Smartphone Gama Lite 64GB", "Celular", "Gama", 480.00, 799.00),
    ("MOTO-001", "Moto elétrica Volt 800W", "Moto elétrica", "Volt", 5200.00, 7490.00),
    ("MOTO-002", "Moto elétrica Volt 1500W", "Moto elétrica", "Volt", 7800.00, 10990.00),
    ("MOTO-003", "Scooter elétrica Zip 500W", "Moto elétrica", "Zip", 3400.00, 4990.00),
    ("ACE-001", "Capa protetora", "Acessório", "Genérica", 8.00, 39.90),
    ("ACE-002", "Película de vidro", "Acessório", "Genérica", 5.00, 29.90),
    ("ACE-003", "Carregador 20W", "Acessório", "Alfa", 25.00, 79.90),
    ("ACE-004", "Cabo USB-C 1m", "Acessório", "Genérica", 9.00, 34.90),
    ("ACE-005", "Fone Bluetooth", "Acessório", "Beta", 55.00, 149.90),
    ("ACE-006", "Power bank 10000mAh", "Acessório", "Gama", 60.00, 139.90),
    ("ACE-007", "Capacete para moto elétrica", "Acessório", "Volt", 90.00, 229.90),
    ("PERF-001", "Perfume Aurora 100ml", "Perfume", "Aurora", 95.00, 219.90),
    ("PERF-002", "Perfume Noir Intenso 100ml", "Perfume", "Noir", 120.00, 289.90),
    ("PERF-003", "Perfume Brisa Feminino 50ml", "Perfume", "Brisa", 70.00, 169.90),
    ("PERF-004", "Perfume Oud Masculino 100ml", "Perfume", "Oud", 150.00, 349.90),
    ("PERF-005", "Kit Perfume Mini 3x30ml", "Perfume", "Aurora", 60.00, 149.90),
    ("PERF-006", "Body Splash Floral 200ml", "Perfume", "Brisa", 22.00, 59.90),
]

ESTOQUE_INICIAL = {"Celular": 8, "Moto elétrica": 3, "Acessório": 40, "Perfume": 20}
# categoria: (repor quando estoque < limite, quantidade a repor)
REPOSICAO = {
    "Celular": (3, 8),
    "Moto elétrica": (1, 3),
    "Acessório": (10, 40),
    "Perfume": (5, 15),
}
FORNECEDORES = {
    "Celular": "Distribuidora Tech Sul",
    "Moto elétrica": "Mobilidade Verde Ltda",
    "Acessório": "Atacado Acessórios RJ",
    "Perfume": "Perfumaria Atacado Rio",
}
# peso de cada categoria na escolha dos itens vendidos
PESO_CATEGORIAS = {"Celular": 28, "Acessório": 35, "Perfume": 32, "Moto elétrica": 5}


def simular(dias: int):
    fim = date.today()
    inicio = fim - timedelta(days=dias - 1)

    produtos = [
        dict(sku=s, nome=n, categoria=c, marca=m, custo=custo, preco=preco)
        for s, n, c, m, custo, preco in PRODUTOS
    ]
    por_categoria = {}
    for p in produtos:
        por_categoria.setdefault(p["categoria"], []).append(p)

    estoque = {p["sku"]: 0 for p in produtos}
    compras, vendas = [], []
    fake = Faker("pt_BR")

    def comprar(dia, p, qtd):
        custo = round(p["custo"] * random.uniform(0.97, 1.03), 2)
        compras.append({
            "data": dia.isoformat(),
            "sku": p["sku"],
            "quantidade": qtd,
            "custo_unitario": custo,
            "fornecedor": FORNECEDORES[p["categoria"]],
        })
        estoque[p["sku"]] += qtd

    # estoque inicial, comprado no primeiro dia
    for p in produtos:
        comprar(inicio, p, ESTOQUE_INICIAL[p["categoria"]])

    contador_venda = 0
    categorias = list(PESO_CATEGORIAS)
    pesos = list(PESO_CATEGORIAS.values())

    for i in range(dias):
        dia = inicio + timedelta(days=i)

        # reposição no início do dia
        if i > 0:
            for p in produtos:
                limite, qtd = REPOSICAO[p["categoria"]]
                if estoque[p["sku"]] < limite:
                    comprar(dia, p, qtd)

        # média de ~2 vendas por dia: sábado vende mais, domingo menos
        faixa = {5: (1, 5), 6: (0, 2)}.get(dia.weekday(), (0, 4))
        for _ in range(random.randint(*faixa)):
            n_itens = random.choices([1, 2, 3], weights=[80, 17, 3])[0]
            itens, usados = [], set()
            for _ in range(n_itens):
                categoria = random.choices(categorias, weights=pesos)[0]
                p = random.choice(por_categoria[categoria])
                if p["sku"] in usados:
                    continue
                qtd = random.randint(1, 3) if categoria == "Acessório" else 1
                if estoque[p["sku"]] < qtd:
                    continue
                usados.add(p["sku"])
                estoque[p["sku"]] -= qtd
                itens.append((p, qtd))
            if not itens:
                continue

            contador_venda += 1
            id_venda = f"V{contador_venda:04d}"
            pagamento = random.choices(PAGAMENTOS, weights=PESO_PAGAMENTOS)[0]
            vendedor = random.choice(VENDEDORES)
            cliente = fake.name()
            for p, qtd in itens:
                desconto = 0.0
                if random.random() < 0.30:
                    desconto = round(p["preco"] * qtd * random.uniform(0.02, 0.08), 2)
                vendas.append({
                    "data": dia.isoformat(),
                    "id_venda": id_venda,
                    "sku": p["sku"],
                    "quantidade": qtd,
                    "preco_unitario": p["preco"],
                    "desconto": desconto,
                    "forma_pagamento": pagamento,
                    "vendedor": vendedor,
                    "cliente": cliente,
                })

    df_produtos = pd.DataFrame(
        PRODUTOS,
        columns=["sku", "nome", "categoria", "marca", "custo_unitario", "preco_tabela"],
    )
    return df_produtos, pd.DataFrame(vendas), pd.DataFrame(compras)


def injetar_erros(vendas: pd.DataFrame, fracao: float = 0.04) -> pd.DataFrame:
    """Corrompe algumas linhas para testar as regras de validação do pipeline."""
    vendas = vendas.copy()
    n = max(4, int(len(vendas) * fracao))
    for k, idx in enumerate(random.sample(list(vendas.index), n)):
        tipo = k % 4
        if tipo == 0:
            vendas.loc[idx, "sku"] = "XXX-999"             # SKU inexistente
        elif tipo == 1:
            vendas.loc[idx, "quantidade"] = 0              # quantidade inválida
        elif tipo == 2:
            vendas.loc[idx, "forma_pagamento"] = "Cheque"  # pagamento fora da lista
        else:
            vendas.loc[idx, "data"] = "31/02/2026"         # data inválida
    return vendas


def main():
    parser = argparse.ArgumentParser(description="Gera dados fictícios da loja.")
    parser.add_argument("--dias", type=int, default=90, help="quantidade de dias simulados")
    parser.add_argument("--seed", type=int, default=42, help="semente para resultados reproduzíveis")
    parser.add_argument("--com-erros", action="store_true", help="injeta linhas inválidas em vendas")
    args = parser.parse_args()

    random.seed(args.seed)
    Faker.seed(args.seed)

    produtos, vendas, compras = simular(args.dias)
    if args.com_erros:
        vendas = injetar_erros(vendas)

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    produtos.to_csv(PASTA_SAIDA / "produtos.csv", index=False, encoding="utf-8")
    vendas.to_csv(PASTA_SAIDA / "vendas.csv", index=False, encoding="utf-8")
    compras.to_csv(PASTA_SAIDA / "compras.csv", index=False, encoding="utf-8")

    print(f"Arquivos gerados em {PASTA_SAIDA}")
    print(f"  produtos: {len(produtos)} linhas")
    print(f"  vendas:   {len(vendas)} linhas ({vendas['id_venda'].nunique()} vendas)")
    print(f"  compras:  {len(compras)} linhas")


if __name__ == "__main__":
    main()
