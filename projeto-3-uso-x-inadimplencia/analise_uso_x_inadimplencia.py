"""
Análise da relação entre uso da plataforma e inadimplência.

Contexto
--------
A empresa vende um software (SaaS) e cobra por assinatura. Um cliente que
fica inadimplente por mais de 60 dias corre o risco de perder o acesso à
plataforma e parar de faturar — por isso a janela de análise escolhida
aqui é justamente os 2 meses (60 dias) anteriores ao início da
inadimplência: é a janela de tempo em que ainda é possível agir antes de
perder o cliente.

Este script:

  1. limpa a base de clientes (remove contas de teste e não definitivas);
  2. segmenta clientes em adimplentes, inadimplentes ativos e
     inadimplentes cancelados;
  3. mede o uso da plataforma (eventos de produto, logins, auditorias e
     arquivos importados) na janela de 2 meses antes do início da
     inadimplência, comparando com uma janela equivalente para clientes
     adimplentes;
  4. cruza esse uso com indicadores de relacionamento (reuniões
     realizadas, reuniões de implantação, tentativas de contato) do time
     de Customer Success, para entender se a falta de contato/onboarding
     também se relaciona com a inadimplência;
  5. cruza clientes que cancelaram com a base de resgates para medir
     quantos cancelamentos ocorreram dentro dos primeiros 30/60 dias de
     inadimplência.

Os números de exemplo no README deste projeto são ilustrativos/arredondados
— este script não inclui nenhuma base de dados real.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

JANELA_ALERTA_DIAS_MESES = 2  # janela de análise: 2 meses antes da inadimplência (limite de 60 dias)


def limpar_base_clientes(clientes: pd.DataFrame, base_ativa: pd.DataFrame) -> pd.DataFrame:
    """Remove contas de teste/não definitivas e normaliza a chave de cliente."""
    clientes = clientes.copy()
    clientes["Documento"] = clientes["Documento"].astype(str).str.strip()
    clientes["Codigo Cliente Legado"] = clientes["Codigo Cliente Legado"].astype(str).str.strip()

    clientes = clientes[clientes["Cliente Teste"] == False]  # noqa: E712
    clientes = clientes[clientes["Tipo"] == "Definitivo"]
    clientes = clientes[~clientes["Razao Social / Nome Completo"].str.contains("teste", case=False, na=False)]

    base_ativa = base_ativa.copy()
    base_ativa["ID Original"] = base_ativa["ID Original"].astype(str).str.strip()
    return clientes


def segmentar_clientes(clientes: pd.DataFrame, base_ativa: pd.DataFrame):
    """Separa a base em adimplentes, inadimplentes ativos e inadimplentes cancelados."""
    ativos = clientes[clientes["Status"] == "Ativo"]
    ativos = ativos[ativos["Codigo Cliente Legado"].isin(base_ativa["ID Original"])]

    cancelados = clientes[clientes["Status"] == "Cancelado"]

    adimplentes = ativos[ativos["Status Financeiro"] == "Adimplente"].copy()
    inadimplentes_ativos = ativos[ativos["Status Financeiro"] == "Inadimplente"].copy()
    inadimplentes_cancelados = cancelados[cancelados["Status Financeiro"] == "Inadimplente"].copy()

    return adimplentes, inadimplentes_ativos, inadimplentes_cancelados


def _colunas_de_data(df: pd.DataFrame) -> list[tuple[str, pd.Timestamp]]:
    """Identifica, num relatório de uso pivotado por data, quais colunas são datas válidas."""
    colunas = []
    for col in df.columns:
        data = pd.to_datetime(col, errors="coerce", dayfirst=True)
        if pd.notna(data):
            colunas.append((col, data))
    return colunas


def uso_na_janela(
    indice_por_cliente: pd.DataFrame,
    codigo_cliente: str,
    data_referencia: pd.Timestamp,
    meses_antes: int = JANELA_ALERTA_DIAS_MESES,
) -> float:
    """Soma o uso (eventos/logins/auditorias/arquivos) de um cliente numa janela de N meses antes de uma data."""
    if pd.isna(data_referencia) or codigo_cliente not in indice_por_cliente.index:
        return np.nan

    data_inicio = data_referencia - pd.DateOffset(months=meses_antes)
    linhas_cliente = indice_por_cliente.loc[[codigo_cliente]]

    colunas_na_janela = [
        col for col, data in _colunas_de_data(indice_por_cliente) if data_inicio <= data <= data_referencia
    ]
    if not colunas_na_janela:
        return np.nan

    return linhas_cliente[colunas_na_janela].sum().sum()


def medir_uso_pre_inadimplencia(
    inadimplentes_ativos: pd.DataFrame,
    eventos_idx: pd.DataFrame,
    logins_idx: pd.DataFrame,
    auditorias_idx: pd.DataFrame,
    arquivos_idx: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula o uso da plataforma nos 2 meses antes do início da inadimplência, por cliente."""
    df = inadimplentes_ativos.copy()
    df["Codigo Cliente Legado"] = df["Codigo Cliente Legado"].astype(str).str.strip()
    df["Data Inicio Inadimplencia"] = pd.to_datetime(
        df["Data Inicio Inadimplencia"], errors="coerce", dayfirst=True
    )
    df["possui_auditoria"] = df["Codigo Cliente Legado"].isin(auditorias_idx.index)

    for nome_metrica, indice in (
        ("uso_eventos", eventos_idx),
        ("uso_logins", logins_idx),
        ("uso_auditorias", auditorias_idx),
        ("uso_arquivos", arquivos_idx),
    ):
        df[f"{nome_metrica}_2m"] = df.apply(
            lambda row: uso_na_janela(indice, row["Codigo Cliente Legado"], row["Data Inicio Inadimplencia"]),
            axis=1,
        )
    return df


def medir_uso_grupo_controle(
    adimplentes: pd.DataFrame,
    data_referencia: pd.Timestamp,
    eventos_idx: pd.DataFrame,
    logins_idx: pd.DataFrame,
    auditorias_idx: pd.DataFrame,
    arquivos_idx: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula o uso na mesma janela de tempo (2 meses) para o grupo de controle de clientes adimplentes."""
    df = adimplentes.copy()
    df["Codigo Cliente Legado"] = df["Codigo Cliente Legado"].astype(str).str.strip()
    df["possui_auditoria"] = df["Codigo Cliente Legado"].isin(auditorias_idx.index)

    for nome_metrica, indice in (
        ("uso_eventos", eventos_idx),
        ("uso_logins", logins_idx),
        ("uso_auditorias", auditorias_idx),
        ("uso_arquivos", arquivos_idx),
    ):
        df[f"{nome_metrica}_2m"] = df.apply(
            lambda row: uso_na_janela(indice, row["Codigo Cliente Legado"], data_referencia), axis=1
        )
    return df


def resumo_uso(df: pd.DataFrame, rotulo: str) -> pd.DataFrame:
    """Gera um resumo comparável (médias) das métricas de uso para um grupo."""
    linhas = {
        "grupo": rotulo,
        "eventos_media": df["uso_eventos_2m"].mean(),
        "logins_media": df["uso_logins_2m"].mean(),
        "arquivos_media": df["uso_arquivos_2m"].mean(),
        "auditorias_media_quem_possui": df.loc[df["possui_auditoria"], "uso_auditorias_2m"].mean(),
    }
    return pd.DataFrame([linhas])


def cruzar_relacionamento_cs(contatos_cs: pd.DataFrame, codigos_cliente: pd.Series) -> pd.DataFrame:
    """
    Filtra os indicadores de relacionamento do time de Customer Success
    (reuniões realizadas, reunião de implantação, tentativas de contato)
    para o grupo de clientes informado.
    """
    contatos_cs = contatos_cs.copy()
    contatos_cs["ID Original"] = contatos_cs["ID Original"].astype(str).str.strip()
    return contatos_cs[contatos_cs["ID Original"].isin(codigos_cliente)]


def indicadores_relacionamento(contatos_filtrados: pd.DataFrame) -> dict:
    """Conta quantos clientes do grupo nunca tiveram reunião, contato ou implantação registrada."""
    return {
        "total_clientes": contatos_filtrados.shape[0],
        "sem_reunioes": int((contatos_filtrados["Reuniões Realizadas"] == 0).sum()),
        "sem_tentativa_contato": int((contatos_filtrados["Tentativas de Contato"] == 0).sum()),
        "sem_implantacao": int((contatos_filtrados["Reuniões 1 Realizadas - Implantação"] == 0).sum()),
    }


def tempo_ate_cancelamento(
    resgates: pd.DataFrame, contratos: pd.DataFrame, clientes: pd.DataFrame
) -> pd.DataFrame:
    """
    Para clientes que cancelaram (resgate), calcula quantos dias se passaram
    entre o início do contrato e o início da inadimplência — usado para medir
    quão rápido a inadimplência levou ao cancelamento.
    """
    contratos = contratos.copy()
    contratos["Codigo Cliente Legado"] = contratos["Codigo Cliente Legado"].astype(str).str.strip()
    contratos = contratos.merge(
        clientes[["Codigo Cliente Legado", "Documento"]], on="Codigo Cliente Legado", how="left"
    )

    resgates = resgates.copy()
    resgates["CPF/CNPJ"] = resgates["CPF/CNPJ"].astype(str).str.replace(r"[^\d]", "", regex=True)

    dados = contratos[["Documento", "Data Inicial"]].merge(
        clientes[["Documento", "Data Inicio Inadimplencia"]], on="Documento", how="left"
    )
    dados["CPF/CNPJ"] = dados["Documento"].astype(str).str.replace(r"[^\d]", "", regex=True)

    resgates = resgates.merge(
        dados[["CPF/CNPJ", "Data Inicial", "Data Inicio Inadimplencia"]], on="CPF/CNPJ", how="left"
    )
    resgates["Data Inicial"] = pd.to_datetime(resgates["Data Inicial"], dayfirst=True, errors="coerce")
    resgates["Data Inicio Inadimplencia"] = pd.to_datetime(
        resgates["Data Inicio Inadimplencia"], dayfirst=True, errors="coerce"
    )
    resgates["dias_ate_inadimplencia"] = (
        resgates["Data Inicio Inadimplencia"] - resgates["Data Inicial"]
    ).dt.days
    return resgates
