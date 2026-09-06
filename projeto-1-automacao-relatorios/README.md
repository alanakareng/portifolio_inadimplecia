[README.md](https://github.com/user-attachments/files/31886673/README.md)
# Automação do tratamento de relatórios de cobrança

**Problema:** todos os dias, o setor de cobrança extrai relatórios do ERP para embasar o trabalho das analistas. O tratamento desses relatórios — formatar telefones, agrupar parcelas por cliente, separar carteiras que exigem tratamento especial, segmentar por ano da dívida — era feito manualmente, planilha por planilha.

**Solução:** três scripts em Python (pandas) que automatizam ponta a ponta o tratamento de cada tipo de relatório (carteira ativa, carteira de clientes cancelados e uma carteira operada com um parceiro), reduzindo um processo de horas para segundos.

## O que cada script faz

| Script | Relatório de entrada | Principais tratamentos |
|---|---|---|
| `tratar_titulos_ativos.py` | Carteira ativa (títulos em aberto) | Formatação de telefones, consolidação de parcelas por cliente, separação de clientes em regime especial, identificação de clientes com 2+ parcelas em aberto, distribuição balanceada entre a equipe |
| `tratar_titulos_cancelados.py` | Carteira de clientes cancelados | Filtro de títulos abaixo do valor mínimo de cobrança, exclusão de clientes com negociação de resgate em andamento, carteira de PDD (180 dias e ~6 meses), segmentação por ano de vencimento |
| `tratar_carteira_parceira.py` | Carteira operada com parceiro | Consolidação por cliente, cálculo de valor total, carteira de PDD e segmentação anual no mesmo padrão da carteira própria |

## Técnicas e bibliotecas

- **Python / pandas** para leitura, limpeza e agregação de dados tabulares (`groupby`, `merge`, tratamento de datas)
- **openpyxl** para geração de planilhas Excel com múltiplas abas e largura de coluna automática
- Lógica de segmentação de carteira por critérios de negócio (tempo de inadimplência, valor mínimo de cobrança, regime tributário especial)
- Distribuição balanceada de carteiras entre analistas

## Impacto

- Processo que antes era manual e levava um tempo considerável passou a ser executado em segundos, todos os dias.
- Padronização do tratamento: menos erro humano, mesma régua de cobrança aplicada de forma consistente entre as diferentes carteiras.
- Analistas passam a receber uma base já pronta para ação, com clientes segmentados e distribuídos.

---

> Os arquivos de entrada (relatórios reais extraídos do ERP) não fazem parte deste repositório por conterem dados de clientes. O código foi adaptado para uso público: nomes de colegas e de parceiros comerciais foram generalizados, e nenhum dado real de cliente está incluído.
