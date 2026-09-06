"""
Tratamento automático do relatório de títulos de clientes cancelados.

Contexto
--------
Clientes que cancelam o contrato mas ainda possuem títulos em aberto
seguem uma régua de cobrança diferente da carteira ativa. Este script:

  1. remove clientes já em regime especial (SPED) e títulos de baixo valor,
     que não entram na régua de cobrança;
  2. exclui da régua quem já possui negociação de resgate em andamento
     (cruzamento com a base de resgates);
  3. separa a carteira de provisão para devedores duvidosos (PDD) — clientes
     com o título mais antigo vencido há exatamente 180 dias, e uma visão
     complementar dos vencidos há ~6 meses;
  4. segmenta a carteira remanescente por ano de vencimento da dívida, o que
     ajuda a priorizar ações por tempo de inadimplência;
  5. distribui as carteiras anuais entre a equipe de cobrança.

Uso
---
    python tratar_titulos_cancelados.py relatorio.xlsx resgates.xlsx

Observação: os arquivos de entrada não fazem parte deste repositório por
conterem informações de clientes.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

import pandas as pd

VALOR_MINIMO_COBRANCA = 50  # títulos abaixo deste valor não entram na régua
MARCADOR_REGIME_ESPECIAL = "S"
DIAS_PDD = 180

EQUIPE_COBRANCA = ["Analista 1", "Analista 2", "Analista 3", "Analista 4"]

COLUNAS_PDD = ["CPF/CNPJ", "Cliente", "Telefone", "Telefone2", "E-mail", "Valor Título", "Vencimento"]
COLUNAS_ANUAIS = [
    "CPF/CNPJ",
    "Cliente",
    "Telefone",
    "Telefone2",
    "E-mail",
    "Valor Título",
    "Valor Total",
    "Vencimento",
    "Responsável",
]


def carregar_bases(caminho_relatorio: str, caminho_resgates: str, linhas_cabecalho: int = 4):
    cancelados = pd.read_excel(caminho_relatorio, skiprows=linhas_cabecalho)
    resgates = pd.read_excel(caminho_resgates)
    return cancelados, resgates


def formatar_telefones(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Telefone"] = "55" + df["DDD"].astype(str) + df["Telefone"].astype(str)
    df["Telefone2"] = "55" + df["DDD2"].astype(str) + df["Telefone2"].astype(str)
    return df.drop(columns=["DDD", "DDD2"], errors="ignore")


def separar_regime_especial(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    mascara = df["CPF/CNPJ"].astype(str).str.contains(MARCADOR_REGIME_ESPECIAL, na=False)
    return df[~mascara], df[mascara]


def filtrar_regua_padrao(cancelados: pd.DataFrame, resgates: pd.DataFrame) -> pd.DataFrame:
    """Remove títulos de baixo valor e clientes com resgate em negociação (sem status de encerramento)."""
    resgates_em_aberto = resgates[resgates["Status"].isnull()]
    filtrado = cancelados[cancelados["Valor Título"] >= VALOR_MINIMO_COBRANCA]
    filtrado = filtrado[~filtrado["CPF/CNPJ"].isin(resgates_em_aberto["CPF/CNPJ"])]
    return filtrado.rename(columns={"Vcto Original": "Vencimento"})


def montar_carteira_pdd(filtrado: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa PDD do dia (vencido há exatamente 180 dias) e PDD do mês (~6 meses)."""
    filtrado = filtrado.copy()
    filtrado["Vencimento"] = pd.to_datetime(filtrado["Vencimento"], format="%d/%m/%Y", errors="coerce")
    ultimo_titulo = filtrado.sort_values("Vencimento").groupby("CPF/CNPJ").last().reset_index()

    corte_180 = pd.Timestamp.today() - pd.Timedelta(days=DIAS_PDD)
    pdd_180 = ultimo_titulo[ultimo_titulo["Vencimento"].dt.date == corte_180.date()]

    corte_6m = pd.Timestamp.today() - pd.DateOffset(months=6)
    pdd_6m = ultimo_titulo[
        (ultimo_titulo["Vencimento"].dt.month == corte_6m.month)
        & (ultimo_titulo["Vencimento"].dt.year == corte_6m.year)
    ]
    # Evita duplicidade entre as duas visões de PDD
    pdd_6m = pdd_6m[~pdd_6m["CPF/CNPJ"].isin(pdd_180["CPF/CNPJ"])]
    return pdd_180, pdd_6m


def montar_carteiras_anuais(filtrado: pd.DataFrame, excluir_cpfs: pd.Series) -> dict[int, pd.DataFrame]:
    """Segmenta a carteira remanescente por ano de vencimento do título mais recente."""
    anuais = filtrado.sort_values("Vencimento").groupby("CPF/CNPJ").last().reset_index()
    valor_total = (
        filtrado.groupby("CPF/CNPJ")["Valor Título"].sum().reset_index(name="Valor Total")
    )
    anuais = anuais.merge(valor_total, on="CPF/CNPJ")
    anuais = anuais[~anuais["CPF/CNPJ"].isin(excluir_cpfs)]

    carteiras = {}
    for ano in sorted(anuais["Vencimento"].dt.year.dropna().unique()):
        carteiras[int(ano)] = anuais[anuais["Vencimento"].dt.year == ano].copy()
    return carteiras


def distribuir_entre_equipe(df: pd.DataFrame, equipe: list[str] = EQUIPE_COBRANCA) -> pd.DataFrame:
    df = df.copy()
    total = len(df)
    if total == 0:
        df["Responsável"] = []
        return df
    tamanho_grupo = max(total // len(equipe), 1)
    responsaveis = [equipe[min(i // tamanho_grupo, len(equipe) - 1)] for i in range(total)]
    df["Responsável"] = responsaveis
    return df


def gerar_relatorio(caminho_relatorio: str, caminho_resgates: str, caminho_saida: str | None = None) -> str:
    cancelados, resgates = carregar_bases(caminho_relatorio, caminho_resgates)
    cancelados, sped = separar_regime_especial(cancelados)
    cancelados = formatar_telefones(cancelados)

    filtrado = filtrar_regua_padrao(cancelados, resgates)
    pdd_180, pdd_6m = montar_carteira_pdd(filtrado)

    excluir = pd.concat([pdd_180["CPF/CNPJ"], pdd_6m["CPF/CNPJ"]])
    carteiras_anuais = montar_carteiras_anuais(filtrado, excluir)
    carteiras_anuais = {ano: distribuir_entre_equipe(df) for ano, df in carteiras_anuais.items()}

    def formatar_datas(d: pd.DataFrame) -> pd.DataFrame:
        return d.assign(**{"Vencimento": d["Vencimento"].dt.strftime("%d/%m/%Y")})

    if caminho_saida is None:
        caminho_saida = f"Cancelados_{date.today().strftime('%d-%m-%Y')}.xlsx"

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        formatar_datas(pdd_180).to_excel(writer, sheet_name="PDD 180 dias", index=False)
        formatar_datas(pdd_6m).to_excel(writer, sheet_name="PDD 6 meses", index=False)
        for ano, carteira in carteiras_anuais.items():
            formatar_datas(carteira).to_excel(writer, sheet_name=str(ano), index=False)

        for sheet in writer.sheets.values():
            for column in sheet.columns:
                maior = max((len(str(c.value)) if c.value else 0 for c in column), default=0)
                sheet.column_dimensions[column[0].column_letter].width = min(maior + 4, 30)

    return caminho_saida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("relatorio", help="Caminho do relatório bruto (.xlsx) de cancelados")
    parser.add_argument("resgates", help="Caminho da base de resgates/negociações em andamento (.xlsx)")
    parser.add_argument("-o", "--saida", help="Caminho do arquivo de saída", default=None)
    args = parser.parse_args()

    caminho = gerar_relatorio(args.relatorio, args.resgates, args.saida)
    print(f"Relatório gerado em: {caminho}")


if __name__ == "__main__":
    sys.exit(main())
