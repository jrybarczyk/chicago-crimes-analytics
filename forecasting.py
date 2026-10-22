# forecasting.py - Lógica de previsão, sem dependência de interface.
#
# Este módulo NÃO importa streamlit e não desenha nada. Toda a lógica que produz
# números vive aqui, para que (a) possa ser testada, (b) possa ser executada por
# scripts de experimento sem abrir o dashboard, e (c) os resultados publicados
# sejam reproduzíveis sem interação manual.
#
# A página pages/03_predicao_crimes.py é apenas a interface sobre estas funções.
#
# Convenções fixadas aqui:
#   * Dias sem ocorrência entram na série com 0 (não são omitidos).
#   * Atributos de lag e janela móvel usam SOMENTE valores anteriores ao dia
#     previsto. O teste tests/test_sem_vazamento.py garante essa propriedade.
#   * Previsão multi-passo (recursiva) e previsão de 1 passo à frente são
#     problemas diferentes e nunca devem ser comparadas entre si.
import numpy as np
import pandas as pd
import holidays
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

__all__ = [
    "serie_diaria", "calcular_metricas", "features_calendario", "features_lags",
    "rodar_prophet", "rodar_random_forest", "naive_sazonal", "climatologia",
    "PROPHET_CPS_PADRAO",
]

# Valor padrão do Prophet para changepoint_prior_scale. Exposto como constante
# porque governa o quanto a tendência estimada no fim do treino é extrapolada —
# a origem da falha do modelo quando o treino termina dentro de uma transição.
PROPHET_CPS_PADRAO = 0.05


# =====================================================================
# Série
# =====================================================================
def serie_diaria(df_filtrado, coluna_data="Date"):
    """Contagem diária de ocorrências, com dias sem ocorrência preenchidos com 0.

    Omitir os dias vazios deslocaria o índice temporal e corromperia
    silenciosamente os atributos defasados.
    """
    s = df_filtrado.resample("D", on=coluna_data).size()
    if s.empty:
        return s.rename("y").rename_axis("ds")
    idx = pd.date_range(s.index.min(), s.index.max(), freq="D")
    return s.reindex(idx, fill_value=0).rename("y").rename_axis("ds")


# =====================================================================
# Métricas
# =====================================================================
def calcular_metricas(y_real, y_prev):
    """MAE, RMSE, MSE, ME (viés), MAPE e sMAPE.

    ME é o erro médio COM sinal. É a métrica que denuncia viés sistemático de
    nível: um modelo que erra o patamar inteiro tem |ME| próximo do MAE, o que
    não aparece em nenhuma das outras métricas.
    """
    y_real = np.asarray(y_real, dtype=float)
    y_prev = np.asarray(y_prev, dtype=float)
    mae = float(mean_absolute_error(y_real, y_prev))
    mse = float(mean_squared_error(y_real, y_prev))
    me = float(np.mean(y_prev - y_real))
    nao_zero = y_real > 0
    mape = (float(np.mean(np.abs((y_real[nao_zero] - y_prev[nao_zero]) / y_real[nao_zero])) * 100)
            if nao_zero.any() else np.nan)
    denom = np.abs(y_real) + np.abs(y_prev)
    smape = float(np.mean(np.where(denom == 0, 0, 2 * np.abs(y_real - y_prev)
                                   / np.where(denom == 0, 1, denom))) * 100)
    return {"MAE": mae, "RMSE": float(np.sqrt(mse)), "MSE": mse, "ME": me,
            "MAPE": mape, "sMAPE": smape, "dias_zero": int((~nao_zero).sum())}


# =====================================================================
# Atributos
# =====================================================================
def features_calendario(idx, anos_feriados):
    us_holidays = holidays.US(years=anos_feriados)
    f = pd.DataFrame(index=idx)
    f["day_of_week"] = idx.dayofweek
    f["day_of_month"] = idx.day
    f["day_of_year"] = idx.dayofyear
    f["month"] = idx.month
    f["quarter"] = idx.quarter
    f["week_of_year"] = idx.isocalendar().week.astype(int).values
    f["is_weekend"] = (idx.dayofweek >= 5).astype(int)
    f["is_holiday"] = np.array([d in us_holidays for d in idx.date], dtype=int)
    f["season"] = ((idx.month % 12) // 3)  # 0=inverno,1=primavera,2=verão,3=outono
    f["is_month_start"] = idx.is_month_start.astype(int)
    return f


def features_lags(y, lags_dias):
    """Lags e janelas móveis usando SOMENTE o passado.

    O shift(1) antes do rolling é obrigatório: sem ele a janela de 7 dias contém
    o próprio dia-alvo e, com os lags de 1 a 6 dias também entre os preditores,
    o alvo passa a ser recuperável por diferença. Ver
    tests/test_sem_vazamento.py::test_atributos_nao_dependem_do_futuro.
    """
    f = pd.DataFrame(index=y.index)
    for lag in range(1, lags_dias + 1):
        f[f"lag_{lag}d"] = y.shift(lag)
    passado = y.shift(1)
    f["rolling_mean_7d"] = passado.rolling(7).mean()
    f["rolling_mean_30d"] = passado.rolling(30).mean()
    f["rolling_std_7d"] = passado.rolling(7).std()
    return f


# =====================================================================
# Prophet
# =====================================================================
def rodar_prophet(treino, teste, seasonality_mode="multiplicative", include_holidays=True,
                  changepoint_prior_scale=PROPHET_CPS_PADRAO):
    """Ajusta o Prophet no treino e prevê TODO o período de teste de uma vez.

    changepoint_prior_scale controla a flexibilidade da tendência. Valores
    menores produzem tendência mais rígida, menos extrapolada. Não há valor
    universalmente melhor: medido em 35 origens (5 tipos de crime x 7 anos de
    teste), 0.001 reduz muito o erro quando a quebra de nível ocorre no fim do
    treino e o aumenta quando a tendência recente era informativa.
    """
    from prophet import Prophet

    model = Prophet(seasonality_mode=seasonality_mode, yearly_seasonality=True,
                    weekly_seasonality=True, daily_seasonality=False,
                    changepoint_prior_scale=changepoint_prior_scale)
    if include_holidays:
        # add_country_holidays usa janela (0, 0): o efeito é estimado apenas no
        # próprio dia do feriado, não em dias vizinhos.
        model.add_country_holidays(country_name="US")

    model.fit(treino.reset_index())  # colunas ds, y
    forecast = model.predict(pd.DataFrame({"ds": teste.index})).set_index("ds")
    return model, forecast, forecast["yhat"].clip(lower=0)


# =====================================================================
# Random Forest
# =====================================================================
def rodar_random_forest(treino, teste, n_estimators=200, lags_dias=14,
                        modo_recursivo=True, n_jobs=-1, random_state=42):
    """Random Forest sobre calendário + atributos históricos.

    modo_recursivo=True : prevê todo o horizonte realimentando as próprias
        previsões, sem consultar nenhum valor observado do teste. É a única
        condição comparável à do Prophet.
    modo_recursivo=False: previsão de 1 passo à frente, com os lags preenchidos
        pelos valores OBSERVADOS dos dias anteriores. Erro menor, mas responde a
        outra pergunta.
    """
    anos = range(treino.index.min().year, teste.index.max().year + 1)
    serie_total = pd.concat([treino, teste])
    cal = features_calendario(serie_total.index, anos)

    # ---- treino ----
    X_treino = pd.concat([cal.loc[treino.index], features_lags(treino, lags_dias)], axis=1).dropna()
    y_treino = treino.loc[X_treino.index]

    model = RandomForestRegressor(n_estimators=n_estimators, random_state=random_state,
                                  n_jobs=n_jobs, min_samples_leaf=2)
    model.fit(X_treino, y_treino)
    colunas = list(X_treino.columns)

    # ---- teste ----
    if not modo_recursivo:
        lags_total = features_lags(serie_total, lags_dias)
        X_teste = pd.concat([cal.loc[teste.index], lags_total.loc[teste.index]], axis=1)[colunas]
        y_prev = pd.Series(model.predict(X_teste), index=teste.index)
    else:
        hist = serie_total.astype(float).copy()
        hist.loc[teste.index] = np.nan
        # to_numpy(copy=True): .values devolve array somente-leitura sob o regime
        # de copy-on-write do pandas >= 2.0 e a atribuição abaixo levantaria
        # ValueError: assignment destination is read-only.
        valores = hist.to_numpy(dtype=float, copy=True)
        pos_inicio = len(treino)
        previs = []
        for i, dia in enumerate(teste.index):
            p = pos_inicio + i
            linha = cal.loc[dia].to_dict()
            for lag in range(1, lags_dias + 1):
                linha[f"lag_{lag}d"] = valores[p - lag]
            ult7, ult30 = valores[p - 7:p], valores[p - 30:p]
            linha["rolling_mean_7d"] = ult7.mean()
            linha["rolling_mean_30d"] = ult30.mean()
            linha["rolling_std_7d"] = ult7.std(ddof=1)
            x = pd.DataFrame([linha])[colunas]
            yhat = max(0.0, float(model.predict(x)[0]))
            valores[p] = yhat
            previs.append(yhat)
        y_prev = pd.Series(previs, index=teste.index)

    importancias = pd.Series(model.feature_importances_, index=colunas).sort_values(ascending=False)
    return y_prev.clip(lower=0).rename("y"), importancias


# =====================================================================
# Linhas de base
# =====================================================================
# Sem um comparador trivial não se sabe quanto do desempenho vem do modelo e
# quanto da estrutura sazonal que qualquer média por dia da semana captura.
def naive_sazonal(treino, teste, periodo=7):
    """Últimos `periodo` valores do treino, repetidos ciclicamente."""
    ult = treino.iloc[-periodo:]
    return pd.Series([float(ult.iloc[i % periodo]) for i in range(len(teste))],
                     index=teste.index, name="y")


def climatologia(treino, teste, dias_janela=364):
    """Média por dia da semana calculada no último ano do treino."""
    corte = treino.index.max() - pd.Timedelta(days=dias_janela)
    ultimo_ano = treino[treino.index >= corte]
    media = ultimo_ano.groupby(ultimo_ano.index.dayofweek).mean()
    return pd.Series([float(media[d]) for d in teste.index.dayofweek],
                     index=teste.index, name="y")
