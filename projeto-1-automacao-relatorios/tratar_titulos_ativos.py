"""
Tratamento automático do relatório de títulos ativos (em aberto).

Contexto
--------
Este script consolida, em segundos, um processamento que antes era feito
manualmente pela equipe de cobrança: a partir do relatório bruto extraído
diariamente do sistema de gestão, ele gera uma base pronta para uso das
analistas, já com telefones formatados, parcelas agrupadas por cliente,
segmentação de carteiras que exigem tratamento especial (ex.: SPED) e
distribuição balanceada de clientes entre a equipe.

O relatório de saída é salvo em um único Excel com múltiplas abas
(visão geral, clientes com 2+ parcelas em aberto, carteira especial).

Uso
---
    python tratar_titulos_ativos.py caminho/do/relatorio.xlsx

Observação: os dados de entrada (relatório extraído do ERP) não fazem
parte deste repositório por conterem informações de clientes.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

# Linhas cujo CPF/CNPJ contém a letra indicadora de regime especial (ex.: SPED)
# devem ser tratadas em separado — não entram na régua de cobrança padrão.
MARCADOR_REGIME_ESPECIAL = "S"

# Time de cobrança responsável pela distribuição balanceada de carteiras.
# Substitua pelos nomes/códigos da sua equipe.
EQUIPE_COBRANCA = ["Analista 1", "Analista 2", "Analista 3", "Analista 4"]

COLUNAS_SAIDA_GERAL = [
    "CPF/CNPJ",
    "Sacado",
    "Telefone",
    "Telefone2",
    "E-mail Principal",
    "Valor Total",
    "Valor Total Com Juros",
    "Qnt Parcelas",
    "Vcto Original",
    "Dias em Atraso",
    "Forma Pagto (Título)",
]

COLUNAS_SAIDA_MULTIPARCELA = COLUNAS_SAIDA_GERAL + ["Responsável"]


def carregar_relatorio(caminho: str, linhas_cabecalho: int = 4) -> pd.DataFrame:
    """Lê o relatório bruto exportado do ERP, pulando o cabeçalho institucional."""
    df = pd.read_excel(caminho, skiprows=linhas_cabecalho)
    return df.rename(columns={"CFRT - CNPJ/CPF c/ dif.": "CPF/CNPJ"})


def formatar_telefones(df: pd.DataFrame) -> pd.DataFrame:
    """Concatena DDD + número com o código do país, criando colunas prontas para discagem/WhatsApp."""
    df = df.copy()
    df["Telefone"] = "55" + df["Cliente - DDD"].astype(str) + df["Cliente - Telefone"].astype(str)
    df["Telefone2"] = "55" + df["Cliente - DDD2"].astype(str) + df["Cliente - Telefone2"].astype(str)
    return df.drop(columns=["Cliente - DDD", "Cliente - DDD2", "Cliente - Telefone", "Cliente - Telefone2"])


def consolidar_por_cliente(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrupa os títulos por CPF/CNPJ, produzindo uma visão única por cliente:
    quantidade de parcelas em aberto, valor total (com e sem encargos) e
    dias de atraso calculados a partir do vencimento mais recente.
    """
    df = df.copy()
    df["Vcto Original"] = pd.to_datetime(df["Vcto Original"], format="%d/%m/%Y", errors="coerce")

    qnt_parcelas = df.groupby("CPF/CNPJ")["Nro NF"].count().reset_index(name="Qnt Parcelas")
    valor_total = df.groupby("CPF/CNPJ")["Valor Título"].sum().reset_index(name="Valor Total")
    valor_com_juros = df.groupby("CPF/CNPJ")["Total a Receber"].sum().reset_index(
        name="Valor Total Com Juros"
    )

    consolidado = (
        df.sort_values("Vcto Original")
        .groupby("CPF/CNPJ")
        .last()
        .reset_index()
        .merge(qnt_parcelas, on="CPF/CNPJ")
        .merge(valor_total, on="CPF/CNPJ")
        .merge(valor_com_juros, on="CPF/CNPJ")
    )
    consolidado["Dias em Atraso"] = (pd.Timestamp.today() - consolidado["Vcto Original"]).dt.days
    return consolidado


def separar_regime_especial(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Isola clientes em regime especial de cobrança (ex.: SPED), que seguem fluxo próprio."""
    mascara = df["CPF/CNPJ"].astype(str).str.contains(MARCADOR_REGIME_ESPECIAL, na=False)
    return df[~mascara], df[mascara]


def distribuir_entre_equipe(df: pd.DataFrame, equipe: list[str] = EQUIPE_COBRANCA) -> pd.DataFrame:
    """Distribui os clientes com múltiplas parcelas em aberto igualmente entre a equipe."""
    df = df.copy()
    total = len(df)
    tamanho_grupo = max(total // len(equipe), 1)
    responsaveis = [equipe[min(i // tamanho_grupo, len(equipe) - 1)] for i in range(total)]
    df["Responsável"] = responsaveis
    return df


def gerar_relatorio(caminho_entrada: str, caminho_saida: str | None = None) -> str:
    df = carregar_relatorio(caminho_entrada)
    df = formatar_telefones(df)
    consolidado = consolidar_por_cliente(df)

    consolidado["Qnt Parcelas"] = pd.to_numeric(consolidado["Qnt Parcelas"], errors="coerce")
    multiparcela = distribuir_entre_equipe(consolidado[consolidado["Qnt Parcelas"] >= 2])

    consolidado, regime_especial = separar_regime_especial(consolidado)
    multiparcela, _ = separar_regime_especial(multiparcela)
    consolidado = consolidado[~consolidado["CPF/CNPJ"].isin(multiparcela["CPF/CNPJ"])]

    def formatar_datas(d: pd.DataFrame) -> pd.DataFrame:
        return d.assign(**{"Vcto Original": d["Vcto Original"].dt.strftime("%d/%m/%Y")})

    consolidado = formatar_datas(consolidado)[COLUNAS_SAIDA_GERAL]
    multiparcela = formatar_datas(multiparcela)[COLUNAS_SAIDA_MULTIPARCELA]
    regime_especial = formatar_datas(regime_especial)[COLUNAS_SAIDA_GERAL]

    if caminho_saida is None:
        caminho_saida = f"Ativos_{date.today().strftime('%d-%m-%Y')}.xlsx"

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        consolidado.to_excel(writer, sheet_name="Geral", index=False)
        multiparcela.to_excel(writer, sheet_name="2+ Parcelas", index=False)
        regime_especial.to_excel(writer, sheet_name="Regime Especial", index=False)

        for sheet in writer.sheets.values():
            for column in sheet.columns:
                maior = max((len(str(c.value)) if c.value else 0 for c in column), default=0)
                sheet.column_dimensions[column[0].column_letter].width = min(maior + 4, 30)

    return caminho_saida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("relatorio", help="Caminho do relatório bruto (.xlsx) extraído do ERP")
    parser.add_argument("-o", "--saida", help="Caminho do arquivo de saída", default=None)
    args = parser.parse_args()

    caminho = gerar_relatorio(args.relatorio, args.saida)
    print(f"Relatório gerado em: {caminho}")


if __name__ == "__main__":
    sys.exit(main())
