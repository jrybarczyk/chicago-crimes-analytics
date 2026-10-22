# Changelog

## 1.1.0 — 2026-10-22

Foco desta versão: caber no Streamlit Community Cloud e tornar os resultados
reproduzíveis fora do dashboard.

### Adicionado
- `forecasting.py`: toda a lógica de previsão, sem `import streamlit`. A página
  `pages/03_predicao_crimes.py` passou a ser só interface.
- `tests/test_sem_vazamento.py`: 7 testes, entre eles um de causalidade que
  perturba `y[i:]` e exige que nenhum atributo na posição `i` mude. Reintroduzir
  o bug de média móvel faz esse teste falhar nomeando
  `rolling_mean_7d`, `rolling_mean_30d` e `rolling_std_7d`.
- `experiments/run_rolling_origin.py`: avaliação com origem deslizante por linha
  de comando, gerando o CSV que sustenta as tabelas do artigo sem interação manual.
- Linhas de base no painel de predição, sempre visíveis: naive sazonal (m = 7) e
  climatologia por dia da semana. A interface avisa quando o modelo não supera a
  melhor delas.
- Métrica ME (erro médio com sinal) ao lado de MAE e RMSE, e aviso automático
  quando |ME| passa de 40% do MAE — o caso em que o erro é de patamar, não de
  sazonalidade.
- Controle de `changepoint_prior_scale` do Prophet na barra lateral, com a
  medida do efeito no texto de ajuda. Em 35 origens avaliadas, reduzir de 0,05
  para 0,001 melhora muito quando a quebra de nível está no fim do treino
  (furtos 2021: MAPE de 54,5% para 17,3%) e piora quando a tendência recente era
  informativa (furto de veículo 2024: de 28,7% para 65,3%). No agregado melhora em
  16 das 35 origens e em 4 das 10 de quebra, com ganho mediano de −0,05 p.p.: é uma
  troca entre dois modos de falha, por isso o padrão do Prophet foi mantido.
- Gráfico da tendência estimada pelo Prophet no período de teste, para tornar
  visível quando a previsão está dominada por extrapolação.
- Aviso de quebra de regime quando o nível médio do teste difere do treino em
  15% ou mais.
- `requirements-dev.txt` e variável de ambiente `CHICAGO_DATA_DIR`.

### Corrigido
- `rodar_random_forest` modo recursivo levantava
  `ValueError: assignment destination is read-only` sob copy-on-write do
  pandas ≥ 2.0 (`hist.values` devolve array somente-leitura). Agora usa
  `hist.to_numpy(dtype=float, copy=True)`.
- Página 01: a "Média de crimes por dia" dividia pelos dias **com** ocorrência,
  superestimando a média em crimes raros (medido em 2022–2024: +24,7% em
  homicídio, +40,7% em incêndio criminoso, +3.109% em tráfico de pessoas). Agora
  divide pelos dias de calendário efetivamente cobertos.
- Página 02: "Variação (1º → último período)" comparava dois valores pontuais —
  na granularidade diária, dois dias quaisquer. Agora compara a média dos
  primeiros e dos últimos 10% dos períodos.
- Página 02: os limites de IQR eram calculados sobre a janela inteira, marcando
  toda a queda pandêmica como "dias atípicos". Agora são calculados por ano.
- Página 04: os popups do mapa eram montados com `iterrows()`, o gargalo quando
  são dezenas de milhares de pontos. Substituído por `zip` sobre as colunas.

### Alterado
- **Memória.** As quatro páginas passaram a escolher os anos ANTES de carregar e
  a usar `load_data(years_range)` em vez de `load_all()` — a função já existia e
  era código morto. O carregador lê por padrão só as 10 colunas que a aplicação
  referencia; as outras 11 (`ID`, `IUCR`, `Description`, `Beat`, `Ward`,
  `Community Area`, `FBI Code`, `X Coordinate`, `Y Coordinate`, `Day`,
  `DayOfWeek`) somam 118 MB dos 215 MB do DataFrame e não eram lidas por nenhum
  gráfico. Para a linha bruta completa há `load_data(..., colunas="todas")`.
  Medido com a pilha da aplicação importada (237 MB só de imports):

  | Cenário | RSS |
  |---|---|
  | Antes: `load_all()` com as 21 colunas | 741 MB |
  | `load_all()` com as colunas da aplicação | 575 MB |
  | O que as páginas fazem agora (triênio) | **347 MB** |
  | Caminho completo de predição, com Prophet e RF ajustados | **377 MB** |

  O piso de memória garantido pelo Streamlit Community Cloud é de 690 MB.
- `@st.cache_data` → `@st.cache_resource` no carregador: `cache_data` guarda uma
  cópia serializada e devolve outra cópia a cada chamada, duplicando o maior
  objeto da aplicação. O DataFrame devolvido é tratado como somente leitura.
- `_carregar` filtra cada arquivo por ano antes do `concat` e libera a lista de
  partes em seguida, reduzindo o pico de memória.
- A página inicial abre no triênio recente, não nos 11 anos.
- Previsões do Prophet e do Random Forest ficam em cache por configuração: um
  clique repetido é instantâneo. Medido com um núcleo: ajuste do Random Forest
  2,0 s mais 4,9 s do laço recursivo de 365 dias; Prophet 0,6 s.
- `warnings.filterwarnings("ignore")` global foi restrito a categorias
  específicas — o filtro global escondia avisos de depreciação que antecipam
  quebras em produção.
- Erros nos modelos passaram a mostrar o traceback (`st.exception`), antes
  engolido pelo `except`.
- Página 01: aviso explícito de que as barras de 00h e 12h estão infladas por
  horário desconhecido codificado por convenção (crime aorístico). Na base
  inteira, 12:00 e 00:00 são os dois carimbos mais frequentes (2,49% e 2,11%).

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
