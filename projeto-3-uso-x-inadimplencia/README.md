[README.md](https://github.com/user-attachments/files/31886838/README.md)
# Uso da plataforma x inadimplência

**Problema:** entender se existe uma relação entre o quanto um cliente usa a plataforma (o produto que a empresa vende) e o risco dele se tornar inadimplente, e se a atenção recebida do time de Customer Success também influencia esse risco.

**Por que 2 meses:** um cliente inadimplente por mais de 60 dias corre o risco de perder o acesso à plataforma e parar de faturar. Por isso a janela de análise escolhida foi justamente os 2 meses (60 dias) anteriores ao início da inadimplência, é a janela em que ainda há tempo de agir antes de perder o cliente.

## O que a análise faz

1. **Limpeza e segmentação:** remove contas de teste/não definitivas e separa a base em três grupos: clientes adimplentes, inadimplentes ainda ativos e inadimplentes que já cancelaram.
2. **Uso da plataforma:** mede, para cada cliente inadimplente, o volume de eventos de produto, logins, auditorias e arquivos importados nos 2 meses antes do início da inadimplência, e compara com uma janela equivalente para um grupo de controle de clientes adimplentes.
3. **Relacionamento com Customer Success:** cruza os inadimplentes com os indicadores de relacionamento do time de sucesso do cliente (reuniões realizadas, reunião de implantação, tentativas de contato), para checar se a falta de contato/onboarding também se relaciona com a inadimplência.
4. **Velocidade até o cancelamento:** para quem cancelou, mede quantos dias se passaram entre o início do contrato/relacionamento e o início da inadimplência.

## Principais achados (ilustrativos)

> Os números abaixo são arredondados/ilustrativos, para preservar dados internos da empresa - a lógica e a metodologia são as mesmas usadas na análise real.

- Clientes inadimplentes usam a plataforma sensivelmente menos, nos 2 meses antes de entrar em inadimplência, do que clientes adimplentes na mesma janela de tempo, em todas as métricas de uso analisadas (eventos de produto, logins, arquivos importados).
- Uma parcela relevante dos clientes inadimplentes nunca teve reunião registrada com o time de Customer Success, e uma parcela ainda maior nunca teve nenhuma tentativa de contato registrada, sugerindo que parte da inadimplência está associada a uma lacuna de relacionamento, não só a um problema financeiro do cliente.
- Entre os clientes que cancelaram, uma parte relevante o fez em menos de 60 dias após o início da inadimplência, reforçando a importância de agir dentro dessa janela.

## Técnicas e bibliotecas

- **Python / pandas / numpy** para cruzamento de múltiplas fontes (cadastro de clientes, contratos, eventos de produto, logins, auditorias, arquivos importados, indicadores de Customer Success)
- Construção de **janelas de tempo móveis** (uso nos N meses antes de uma data de referência que varia por cliente) usando índices por chave de cliente
- Comparação entre grupo de risco (inadimplentes) e grupo de controle (adimplentes) na mesma janela de tempo
- Cruzamento de bases para medir tempo entre eventos (início do contrato → início da inadimplência → cancelamento)

## Aplicação prática

Essa análise serve como insumo para o time identificar, proativamente, pontos de atenção que antecedem a inadimplência (queda de uso, ausência de contato/onboarding), e não apenas para explicar a inadimplência depois que ela já aconteceu.

---

> Nenhuma base de dados real está incluída neste repositório — apenas o código da análise, com nomes de colegas, clientes e caminhos de arquivo generalizados.
