[README.md](https://github.com/user-attachments/files/31886798/README.md)
# Cálculo do caixa (recuperação) da cobrança

**Problema:** medir corretamente quanto do dinheiro recebido em atraso é, de fato, resultado do trabalho da cobrança — e não apenas o cliente pagando naturalmente no primeiro dia útil após um vencimento em fim de semana.

**Solução:** uma regra de corte que varia conforme o dia da semana em que o pagamento foi feito (e considera feriados nacionais), aplicada título a título, para isolar com precisão a recuperação atribuível à atuação da equipe.

## A regra de negócio

Um título vencido numa sexta-feira e pago na segunda-feira seguinte tem, tecnicamente, 3 dias de atraso — mas isso não significa nenhuma ação de cobrança: é só o primeiro dia útil disponível para pagamento. O mesmo vale, em menor escala, para vencimentos em véspera de feriado.

A regra implementada em `calculo_caixa.py` define um corte diferente por dia da semana da baixa (pagamento):

- **Segunda-feira:** corte de 3 dias (ignora vencimentos de sexta, sábado e domingo)
- **Terça-feira após feriado na segunda:** corte de 2 dias
- **Terça (normal), quarta, quinta ou sexta:** corte de 1 dia

## Evolução em relação ao método anterior

O cálculo já existia antes, era feito usando Excel e usava um **corte fixo de D-3** (`metodo_anterior.py`), igual para qualquer dia da semana. Isso tinha um efeito colateral não percebido: **descartava também títulos vencidos numa sexta-feira**, que ficam a 3-4 dias "de atraso" só por causa do fim de semana, subestimando a recuperação real gerada pela cobrança.

A régua por dia da semana corrigiu essa distorção e passou a capturar corretamente a recuperação de títulos vencidos às sextas-feiras, trazendo esse cálculo, antes feito de forma aproximada, para dentro do setor com mais precisão.

## Técnicas e bibliotecas

- **Python / pandas** para manipulação de datas e regras condicionais aplicadas linha a linha
- **holidays** para considerar feriados nacionais no cálculo do corte
- Modelagem de uma regra de negócio não trivial (dependente de dia da semana + feriados) de forma testável e reutilizável

---

> Os dados de entrada (relatório de baixas) não fazem parte deste repositório por conterem informações de clientes.
