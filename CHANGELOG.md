# Changelog

## Não lançado — 2026-10-16

- Aplicação e páginas organizadas na raiz, com dependências e configuração Streamlit centralizadas.
- Dados movidos para `data/processed/` e documentação acadêmica para `docs/`.
- Instruções de execução e deploy atualizadas; URL do repositório corrigida na citação.
- Dev Container alinhado ao Python 3.12 e à nova estrutura.
- Pasta `paper/` mantida apenas localmente, fora do versionamento.

## 1.0.0 — 2026-10-03

Versão de publicação. Em relação ao código original do TCC (2025):

### Corrigido
- Random Forest: atributos históricos (lags e médias móveis) calculados apenas com
  valores anteriores ao dia previsto, e modo recursivo (multi-passo) que coloca o
  modelo na mesma condição do Prophet.
- `NameError` na aba de clusters quando outra visualização estava selecionada.
- Gráfico de sazonalidade mensal quebrava quando faltava um mês nos dados.
- Importar `app.py` renderizava a página inicial dentro das subpáginas.
- Filtro vazio mostrava silenciosamente o dataset inteiro.

### Alterado
- Carregamento centralizado em `data_loader.py`, dados em Parquet (92 MB em vez de
  500 MB de CSV), tipos otimizados (215 MB em memória para 2,75 milhões de linhas).
- DBSCAN com distância haversine e raio em metros.
- Métricas: MAE, RMSE, MAPE (dias com y > 0) e sMAPE; ano de teste contíguo ao treino.
- Séries diárias com dias sem ocorrência preenchidos com zero.

### Adicionado
- Comparação lado a lado Prophet × Random Forest no dashboard.
- `paper/`: experimento com origem deslizante, figuras e manuscrito.
- Configuração para Streamlit Community Cloud.
