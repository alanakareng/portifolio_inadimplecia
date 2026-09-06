"""
Cálculo do caixa (recuperação) gerado pelo setor de cobrança.

Contexto
--------
Nem todo pagamento recebido depois do vencimento é, de fato, resultado do
trabalho da cobrança. Dois pontos tornam esse cálculo menos trivial do que
"somar tudo que foi pago em atraso":

1. Só entram títulos cuja baixa (pagamento) ocorreu depois do vencimento.
2. Um título que vencia num fim de semana e foi pago na segunda-feira
   seguinte NÃO é uma recuperação da cobrança — é apenas o cliente pagando
   no primeiro dia útil, sem qualquer ação da equipe. O mesmo vale, em
   menor grau, para vencimentos em véspera de feriado.

Este módulo aplica uma regra de corte que varia de acordo com o dia da
semana em que o pagamento (baixa) ocorreu, considerando também feriados
nacionais, para isolar apenas a recuperação efetivamente atribuível à
atuação da cobrança.

Uso
---
    from calculo_caixa import calcular_recuperacao_cobranca_periodo

    total, detalhado = calcular_recuperacao_cobranca_periodo(
        df, col_vencimento="Vcto Original", col_baixa="Data Baixa", col_valor="Total Recebido"
    )

Veja `metodo_anterior.py` para o método de corte fixo (D-3) usado antes
desta versão, e o README deste projeto para o comparativo entre os dois.
"""

from __future__ import annotations

import pandas as pd
import holidays

BR_HOLIDAYS = holidays.Brazil()


def calcular_corte(data_baixa: pd.Timestamp) -> int | None:
    """
    Define, para uma data de baixa (pagamento), quantos dias de atraso mínimo
    um título precisa ter para ser considerado uma recuperação da cobrança.

    A regra evita contar como "recuperação" pagamentos de títulos vencidos em
    fins de semana e quitados no primeiro dia útil seguinte:

    - Segunda-feira: corte de 3 dias (ignora vencimentos de sexta/sábado/domingo).
    - Terça-feira após feriado na segunda: corte de 2 dias.
    - Terça-feira normal, quarta, quinta ou sexta: corte de 1 dia.
    - Sábado ou domingo: sem regra (pagamentos não costumam ser baixados nesses dias).
    """
    dia_semana = data_baixa.weekday()  # 0=segunda ... 4=sexta, 5=sábado, 6=domingo
    dia_anterior_foi_feriado = (data_baixa - pd.Timedelta(days=1)) in BR_HOLIDAYS

    if dia_semana == 0:
        return 3
    if dia_semana == 1:
        return 2 if dia_anterior_foi_feriado else 1
    if dia_semana in (2, 3, 4):
        return 1
    return None


def calcular_recuperacao_cobranca_periodo(
    df: pd.DataFrame, col_vencimento: str, col_baixa: str, col_valor: str
) -> tuple[float, pd.DataFrame]:
    """
    Calcula o total de caixa atribuível à cobrança em um período, aplicando o
    corte dia a dia (cada título usa a regra correspondente ao dia da semana
    da sua própria data de baixa).

    Retorna o total recuperado e o detalhamento dos títulos considerados.
    """
    df = df.copy()
    df[col_vencimento] = pd.to_datetime(df[col_vencimento], dayfirst=True, errors="coerce")
    df[col_baixa] = pd.to_datetime(df[col_baixa], dayfirst=True, errors="coerce")

    atrasados = df[df[col_baixa] > df[col_vencimento]].copy()
    atrasados["dias_atraso"] = (atrasados[col_baixa] - atrasados[col_vencimento]).dt.days
    atrasados["corte_dias"] = atrasados[col_baixa].apply(calcular_corte)
    atrasados = atrasados.dropna(subset=["corte_dias"])

    recuperados = atrasados[atrasados["dias_atraso"] >= atrasados["corte_dias"]]
    total = recuperados[col_valor].sum()

    return total, recuperados


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("relatorio", help="Caminho do relatório de baixas (.xlsx)")
    parser.add_argument("--vencimento", default="Vcto Original")
    parser.add_argument("--baixa", default="Data Baixa")
    parser.add_argument("--valor", default="Total Recebido")
    args = parser.parse_args()

    baixas = pd.read_excel(args.relatorio, skiprows=4)
    total, _ = calcular_recuperacao_cobranca_periodo(baixas, args.vencimento, args.baixa, args.valor)
    print(f"Total recuperado pela cobrança: R$ {total:,.2f}")
