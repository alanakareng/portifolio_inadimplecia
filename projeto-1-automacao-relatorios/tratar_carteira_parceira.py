"""
Tratamento automático da carteira de cobrança de um parceiro operacional.

Contexto
--------
Além da carteira própria, o setor também trata a cobrança de uma carteira
operada em parceria com terceiros, cujo relatório de origem chega em um
layout diferente. Este script normaliza esse relatório para o mesmo padrão
usado internamente: consolida parcelas por cliente, calcula o valor total
já arredondado para cobrança, separa clientes com 2+ parcelas em aberto,
monta a carteira de PDD (~6 meses) e segmenta o restante por ano de
vencimento.

Uso
---
    python tratar_carteira_parceira.py relatorio_parceiro.xlsx

Observação: o arquivo de entrada não faz parte deste repositório por
conter informações de clientes.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import date

import pandas as pd

COLUNAS_SAIDA = [
    "CPF/CNPJ",
    "Sacado",
    "Valor Título",
    "Valor Total",
    "Parcelas",
    "Cód Sacado",
    "Vencimento",
    "Endereço Cobrança",
    "UF",
    "CEP",
    "Telefone 1",
    "Telefone 2",
    "E-mail",
]


def carregar_relatorio(caminho: str, linhas_cabecalho: int = 4) -> pd.DataFrame:
    df = pd.read_excel(caminho, header=linhas_cabecalho)
    return df[~(df["CPF/CNPJ"].isna() & df["Sacado"].isna())]


def consolidar_por_cliente(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula parcelas em aberto e valor total (arredondado para cima) por cliente."""
    df = df.copy()
    df["Parcelas"] = df.groupby("CPF/CNPJ")["CPF/CNPJ"].transform("count")
    df["Valor Total"] = df.groupby("CPF/CNPJ")["Valor Título"].transform("sum")

    consolidado = df.sort_values("Vcto Original").groupby("CPF/CNPJ").last().reset_index()
    consolidado["Valor Total"] = consolidado["Valor Total"].apply(
        lambda x: math.ceil(x) if pd.notna(x) else x
    )
    return consolidado.rename(columns={"Vcto Original": "Vencimento"})


def montar_pdd_6_meses(consolidado: pd.DataFrame) -> pd.DataFrame:
    consolidado = consolidado.copy()
    consolidado["Vencimento"] = pd.to_datetime(
        consolidado["Vencimento"], format="%d/%m/%Y", errors="coerce"
    )
    ultimo_titulo = consolidado.sort_values("Vencimento").groupby("CPF/CNPJ").last().reset_index()

    corte_6m = pd.Timestamp.today() - pd.DateOffset(months=6)
    return ultimo_titulo[
        (ultimo_titulo["Vencimento"].dt.month == corte_6m.month)
        & (ultimo_titulo["Vencimento"].dt.year == corte_6m.year)
    ]


def montar_carteiras_anuais(consolidado: pd.DataFrame, excluir_cpfs: pd.Series) -> dict[int, pd.DataFrame]:
    consolidado = consolidado.copy()
    consolidado["Vencimento"] = pd.to_datetime(
        consolidado["Vencimento"], format="%d/%m/%Y", errors="coerce"
    )
    anuais = consolidado.sort_values("Vencimento").groupby("CPF/CNPJ").last().reset_index()
    anuais = anuais[~anuais["CPF/CNPJ"].isin(excluir_cpfs)]

    carteiras = {}
    for ano in sorted(anuais["Vencimento"].dt.year.dropna().unique()):
        carteiras[int(ano)] = anuais[anuais["Vencimento"].dt.year == ano].copy()
    return carteiras


def gerar_relatorio(caminho_entrada: str, caminho_saida: str | None = None) -> str:
    geral = carregar_relatorio(caminho_entrada)
    consolidado = consolidar_por_cliente(geral)

    consolidado["Parcelas"] = pd.to_numeric(consolidado["Parcelas"], errors="coerce")
    multiparcela = consolidado[consolidado["Parcelas"] >= 2]

    pdd_6m = montar_pdd_6_meses(consolidado)
    carteiras_anuais = montar_carteiras_anuais(consolidado, pdd_6m["CPF/CNPJ"])

    def formatar_datas(d: pd.DataFrame) -> pd.DataFrame:
        d = d.copy()
        d["Vencimento"] = pd.to_datetime(d["Vencimento"], errors="coerce").dt.strftime("%d/%m/%Y")
        return d

    if caminho_saida is None:
        caminho_saida = f"CarteiraParceira_{date.today().strftime('%d-%m-%Y')}.xlsx"

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        geral.to_excel(writer, sheet_name="Geral", index=False)
        formatar_datas(consolidado).to_excel(writer, sheet_name="Consolidado", index=False)
        formatar_datas(multiparcela).to_excel(writer, sheet_name="2+ Parcelas", index=False)
        formatar_datas(pdd_6m).to_excel(writer, sheet_name="PDD 6 meses", index=False)
        for ano, carteira in carteiras_anuais.items():
            formatar_datas(carteira).to_excel(writer, sheet_name=str(ano), index=False)

        for sheet in writer.sheets.values():
            for column in sheet.columns:
                maior = max((len(str(c.value)) if c.value else 0 for c in column), default=0)
                sheet.column_dimensions[column[0].column_letter].width = maior + 4

    return caminho_saida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("relatorio", help="Caminho do relatório bruto (.xlsx) da carteira parceira")
    parser.add_argument("-o", "--saida", help="Caminho do arquivo de saída", default=None)
    args = parser.parse_args()

    caminho = gerar_relatorio(args.relatorio, args.saida)
    print(f"Relatório gerado em: {caminho}")


if __name__ == "__main__":
    sys.exit(main())
