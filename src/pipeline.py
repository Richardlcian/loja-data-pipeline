"""Orquestra o ETL: extrair -> normalizar -> validar -> calcular -> carregar.
Execute na raiz do projeto:  python -m src.pipeline"""
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

import pandas as pd

from config import settings
from src import checks, extract, load, notificar, transform, validate

log = logging.getLogger("pipeline")


def _rejeitadas_originais(bruto: pd.DataFrame, rejeitadas: pd.DataFrame) -> pd.DataFrame:
    """Devolve as linhas rejeitadas como vieram da planilha, com o motivo ao lado."""
    return bruto.loc[rejeitadas.index].assign(motivo_rejeicao=rejeitadas["motivo_rejeicao"])


def executar(dados: dict, con) -> dict:
    """Roda a transformação e a carga com os dados já extraídos. Retorna um resumo."""
    produtos, prod_rej = validate.validar_produtos(transform.normalizar_produtos(dados["produtos"]))
    skus = set(produtos["sku"])

    vendas_n = transform.normalizar_vendas(dados["vendas"])
    vendas_v, vendas_rej = validate.validar_vendas(vendas_n, skus)
    compras_n = transform.normalizar_compras(dados["compras"])
    compras_v, compras_rej = validate.validar_compras(compras_n, skus)

    vendas = transform.calcular_vendas(vendas_v, produtos)
    compras = transform.preparar_compras(compras_v)
    dim_tempo = transform.gerar_dim_tempo(vendas["data"], compras["data"])

    load.criar_schema(con)
    try:
        load.sincronizar_produtos(con, produtos)
        load.sincronizar_vendedores(con, vendas)
        load.sincronizar_dim_tempo(con, dim_tempo)
        load.recarregar_fatos(con, vendas, compras)
        con.commit()
    except Exception:
        con.rollback()
        log.exception("Falha na carga; rollback executado")
        raise

    # reconciliação: o que foi carregado bate com o que foi calculado?
    n_banco, soma_banco = con.execute(
        "SELECT COUNT(*), COALESCE(ROUND(SUM(valor_total), 2), 0) FROM fato_vendas").fetchone()
    soma_calc = round(float(vendas["valor_total"].sum()), 2)
    if n_banco != len(vendas) or abs(soma_banco - soma_calc) > 0.01:
        log.error("Reconciliação falhou: banco=%s/%s | calculado=%s/%s",
                  n_banco, soma_banco, len(vendas), soma_calc)

    return {
        "vendas_carregadas": len(vendas),
        "compras_carregadas": len(compras),
        "carregadas": {"produtos": len(produtos), "vendas": len(vendas), "compras": len(compras)},
        "faturamento": soma_calc,
        "rejeitadas": {
            "produtos": _rejeitadas_originais(dados["produtos"], prod_rej),
            "vendas": _rejeitadas_originais(dados["vendas"], vendas_rej),
            "compras": _rejeitadas_originais(dados["compras"], compras_rej),
        },
    }


def salvar_rejeitadas(rejeitadas: dict) -> None:
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for nome, df in rejeitadas.items():
        arquivo = settings.PROCESSED_DIR / f"rejeitadas_{nome}.csv"
        if len(df):
            df.to_csv(arquivo, index=False, encoding="utf-8")
            log.warning("%d linhas rejeitadas de '%s' salvas em %s", len(df), nome, arquivo.name)
        elif arquivo.exists():
            arquivo.unlink()  # evita ler um arquivo antigo de uma execução anterior


def registrar_alertas(alertas: list[str]) -> None:
    """Grava os alertas em logs/ALERTAS.txt (apaga o arquivo se não há alertas) e avisa por e-mail."""
    arquivo = settings.LOGS_DIR / "ALERTAS.txt"
    if not alertas:
        arquivo.unlink(missing_ok=True)
        log.info("Verificações de qualidade: nenhum alerta")
        return
    texto = "\n".join(f"- {a}" for a in alertas)
    for a in alertas:
        log.warning("ALERTA: %s", a)
    arquivo.write_text(f"Alertas de {datetime.now():%d/%m/%Y %H:%M}\n\n{texto}\n", encoding="utf-8")
    notificar.enviar_email("[Loja] Alertas nos dados", texto)


def rodar() -> None:
    dados = extract.extrair_tudo()
    if not settings.USE_SAMPLE:
        extract.salvar_snapshot(dados)

    con = load.conectar()
    try:
        resultado = executar(dados, con)
        alertas = checks.verificar(con, resultado, verificar_frescor=not settings.USE_SAMPLE)
    finally:
        con.close()

    salvar_rejeitadas(resultado["rejeitadas"])
    registrar_alertas(alertas)
    log.info("Pipeline finalizado: %d vendas, %d compras, faturamento R$ %.2f",
             resultado["vendas_carregadas"], resultado["compras_carregadas"], resultado["faturamento"])


def main() -> None:
    settings.LOGS_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[RotatingFileHandler(settings.LOGS_DIR / "pipeline.log", maxBytes=1_000_000,
                                      backupCount=5, encoding="utf-8"),
                  logging.StreamHandler()],
    )
    modo = "dados fictícios" if settings.USE_SAMPLE else "planilha real"
    log.info("Início do pipeline (%s)", modo)
    try:
        rodar()
    except Exception as erro:
        log.exception("Pipeline falhou")
        notificar.enviar_email(
            "[Loja] Pipeline FALHOU",
            f"O pipeline falhou em {datetime.now():%d/%m/%Y %H:%M}.\n\nErro: {erro!r}\n\n"
            "Veja logs/pipeline.log para os detalhes.")
        raise


if __name__ == "__main__":
    main()
