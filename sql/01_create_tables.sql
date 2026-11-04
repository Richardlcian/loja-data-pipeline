CREATE TABLE IF NOT EXISTS dim_produto (
    id_produto          INTEGER PRIMARY KEY AUTOINCREMENT,
    sku                 TEXT NOT NULL UNIQUE,
    nome                TEXT NOT NULL,
    categoria           TEXT NOT NULL,
    marca               TEXT,
    custo_unitario      REAL NOT NULL CHECK (custo_unitario>=0),
    preco_tabela        REAL NOT NULL CHECK (preco_tabela>=0)
);

CREATE TABLE IF NOT EXISTS dim_cliente (
    id_cliente          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                TEXT NOT NULL,
    cidade               TEXT
);

CREATE TABLE IF NOT EXISTS dim_vendedor (
    id_vendedor        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome               TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_tempo (
    data               TEXT PRIMARY KEY,   -- AAAA-MM-DD
    ano                INTEGER,
    mes                INTEGER,
    dia                INTEGER,
    dia_semana         INTEGER,            -- 0 = segunda
    nome_dia           TEXT,
    trimestre          INTEGER
);

CREATE TABLE IF NOT EXISTS fato_vendas (
    id_item            INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venda           TEXT NOT NULL,
    data               TEXT NOT NULL REFERENCES dim_tempo(data),
    id_produto         INTEGER NOT NULL REFERENCES dim_produto(id_produto),
    id_cliente         INTEGER REFERENCES dim_cliente(id_cliente),
    id_vendedor        INTEGER REFERENCES dim_vendedor(id_vendedor),
    quantidade         INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario     REAL NOT NULL CHECK (preco_unitario >= 0),
    desconto           REAL NOT NULL DEFAULT 0,
    forma_pagamento    TEXT NOT NULL,
    valor_total        REAL NOT NULL,
    custo_total        REAL NOT NULL,
    UNIQUE (id_venda, id_produto)
);

CREATE TABLE IF NOT EXISTS fato_compras (
    id_compra        INTEGER PRIMARY KEY AUTOINCREMENT,
    data             TEXT NOT NULL REFERENCES dim_tempo(data),
    id_produto       INTEGER NOT NULL REFERENCES dim_produto(id_produto),
    quantidade       INTEGER NOT NULL CHECK (quantidade > 0),
    custo_unitario   REAL NOT NULL,
    fornecedor       TEXT
);