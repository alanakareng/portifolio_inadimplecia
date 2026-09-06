"""
Método anterior de cálculo de recuperação da cobrança (referência histórica).

Este arquivo documenta, para efeito de comparação, a regra usada antes da
versão em `calculo_caixa.py`: um corte FIXO de D-3 (o pagamento só contava
como recuperação se ocorresse 3 dias ou mais após o vencimento).

Problema identificado
----------------------
Um corte fixo de D-3 tratava igualmente todos os dias da semana. Na
prática, isso descartava títulos vencidos numa sexta-feira e pagos na
segunda ou terça seguinte — que ficam a 3 ou 4 dias de "atraso" apenas por
causa do fim de semana, mas cujo atraso REAL (em dias úteis) era de 0 ou 1
dia. O efeito colateral era o oposto do desejado: em vez de excluir só os
pagamentos "naturais" de vencimentos de fim de semana, o corte fixo também
excluía uma parte de vencimentos de sexta-feira, subestimando a recuperação
de cobrança.

A versão atual (`calculo_caixa.py`) resolve isso aplicando um corte que
varia conforme o dia da semana da baixa — e feriados —, o que passou a
capturar corretamente também os títulos vencidos na sexta-feira.
"""

from __future__ import annotations

import pandas as pd
import holidays

BR_HOLIDAYS = holidays.Brazil(state="SP")

CORTE_FIXO_DIAS = 3  # D-3: regra antiga, mesmo corte para qualquer dia da semana


def calcular_recuperacao_cobranca_metodo_anterior(
    df: pd.DataFrame, col_vencimento: str, col_baixa: str, col_valor: str
) -> tuple[float, pd.DataFrame]:
    """Reproduz o método antigo (corte fixo D-3) apenas para fins de comparação."""
    df = df.copy()
    df[col_vencimento] = pd.to_datetime(df[col_vencimento], dayfirst=True, errors="coerce")
    df[col_baixa] = pd.to_datetime(df[col_baixa], dayfirst=True, errors="coerce")

    atrasados = df[df[col_baixa] > df[col_vencimento]].copy()
    atrasados["dias_atraso"] = (atrasados[col_baixa] - atrasados[col_vencimento]).dt.days

    recuperados = atrasados[atrasados["dias_atraso"] >= CORTE_FIXO_DIAS]
    total = recuperados[col_valor].sum()

    return total, recuperados
