# Metodologia de previsão

Prophet e Random Forest recebem a mesma série diária. Dias sem ocorrência são
preenchidos com zero. O ano de teste é sempre o ano seguinte ao fim do treino.

Os atributos de lag e média móvel do Random Forest usam apenas valores anteriores
ao dia previsto. O modo recursivo gera a previsão de todo o ano, incorporando as
próprias previsões aos passos seguintes, sem consultar os valores reais do teste.
Isso permite compará-lo à previsão do Prophet para o mesmo horizonte.

O dashboard calcula MAE, RMSE, MAPE (apenas nos dias com valor real maior que zero)
e sMAPE. Os resultados dependem do período e do tipo de crime selecionados.

A análise espacial usa DBSCAN com distância haversine e raio informado em metros.
A base contém horários recorrentes como 00:00 e 12:00 que exigem cuidado na
interpretação de padrões dentro de um mesmo dia.
