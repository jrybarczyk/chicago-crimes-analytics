# Metodologia de previsão

Toda a lógica descrita aqui vive em `forecasting.py`, sem dependência de
interface, e é exercitada por `tests/` e por
`experiments/run_rolling_origin.py`. O dashboard é só uma das formas de chamá-la.

## Série

Prophet e Random Forest recebem a mesma série diária. Dias sem ocorrência são
preenchidos com zero — omiti-los deslocaria o índice temporal e corromperia os
atributos defasados. O ano de teste é sempre o ano seguinte ao fim do treino,
para não deixar lacuna na série.

## Horizonte

Esta é a distinção que mais importa na leitura dos resultados:

- **Multi-passo**: Prophet e Random Forest em modo recursivo preveem o período
  de teste inteiro sem ver nenhum valor observado desse período. São os dois
  únicos comparáveis entre si.
- **Um passo à frente**: o Random Forest nesse modo conhece a contagem observada
  do dia anterior. Produz erro menor, mas responde a outra pergunta
  (dimensionar o dia seguinte, não planejar o ano).

Misturar os dois numa mesma tabela sem essa ressalva produz comparações que
parecem favorecer o Random Forest por razões que nada têm a ver com o modelo.

## Vazamento

Os atributos de lag e de janela móvel usam apenas valores anteriores ao dia
previsto: há um `shift(1)` antes de cada `rolling`. Sem ele, a janela de 7 dias
contém o próprio dia-alvo e, como os lags de 1 a 6 dias também estão entre os
preditores, o alvo passa a ser recuperável por diferença. O efeito é silencioso
— nenhuma exceção, curvas plausíveis — e grande: no recorte de assaltos de 2018
o MAPE cai de 13,37% para 10,26%, o bastante para inverter a conclusão de uma
comparação entre modelos.

`tests/test_sem_vazamento.py::test_atributos_nao_dependem_do_futuro` perturba
`y[i:]` e exige que nenhum atributo na posição `i` mude. Reintroduzir o bug faz
o teste falhar nomeando as três colunas contaminadas.

## Linhas de base

Nenhuma métrica é interpretável sem um comparador trivial. O painel e o script
de experimento reportam sempre:

- **Naive sazonal (m = 7)**: os sete últimos valores do treino, repetidos.
- **Climatologia por dia da semana**: média de cada dia da semana no último ano
  de treino.

Ambas preveem o horizonte inteiro sem acesso a observações do teste. Em 35
origens avaliadas (5 tipos de crime × 7 anos de teste), o Random Forest
recursivo é estatisticamente indistinguível da climatologia (Wilcoxon pareado
sobre o MAE, p = 0,72).

## Métricas

MAE e RMSE como principais; MAPE e sMAPE como secundárias — o MAPE é
assimétrico, indefinido em dias com zero ocorrências e instável quando o nível
da série muda. O ME (erro médio com sinal) é reportado junto porque é a única
das métricas que denuncia viés de patamar: na previsão de furtos para 2021 o
Prophet tem MAE de 62,98 e ME de −62,67, isto é, praticamente todo o erro é
viés de nível, não erro de sazonalidade.

## Tendência do Prophet

A tendência linear por partes é extrapolada a partir da taxa estimada no fim do
treino. Quando o treino termina dentro de uma transição — o caso de 2020 —, a
transição inteira é projetada para a frente. `changepoint_prior_scale` controla
essa flexibilidade e está exposto na interface, mas não há valor universalmente
melhor: medido nas 35 origens, 0,001 melhora em 16 delas e piora nas outras 19, com ganho
mediano de −0,05 ponto percentual, e a mediana sob quebra de regime passa de 27,11%
para 28,68% — não há ganho agregado onde ele seria mais necessário.

## Dados

A base contém horários recorrentes como 00:00 e 12:00 que exigem cuidado na
interpretação de padrões dentro de um mesmo dia: são as duas horas modais do
conjunto, e os carimbos exatos 12:00 e 00:00 concentram 2,49% e 2,11% de todos
os registros, sendo os dois mais frequentes entre os 1.440 possíveis. É horário
desconhecido codificado por convenção (crime aorístico), não comportamento
urbano. Por isso toda a modelagem opera em granularidade diária.

A análise espacial usa DBSCAN com distância haversine e raio informado em
metros.
