# pages/03_predicao_crimes.py - Previsão diária de crimes (Prophet × Random Forest)
#
# Correções em relação à versão anterior:
#   * As médias móveis e os lags do Random Forest usam apenas valores
#     ANTERIORES ao dia previsto (antes a média móvel incluía o próprio alvo,
#     o que vazava a resposta para o modelo e inflava as métricas).
#   * O Random Forest pode prever de forma recursiva (multi-passo), usando as
#     próprias previsões como histórico, exatamente como o Prophet. Só assim a
#     comparação entre os dois modelos é justa.
#   * Dias sem ocorrências entram na série com 0 (antes eram omitidos).
#   * MAPE é calculado só nos dias com valor real > 0 e acompanhado do sMAPE,
#     que não explode quando há zeros.
import sys
import os
import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import holidays
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Configuração da página DEVE SER SEMPRE A PRIMEIRA COISA
st.set_page_config(page_title="Predição Crimes", page_icon="🔮", layout="wide")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_all  # noqa: E402

warnings.filterwarnings("ignore")


# =====================================================================
# Utilidades
# =====================================================================
def serie_diaria(df_filtrado):
    """Contagem diária de crimes, com dias sem ocorrência preenchidos com 0."""
    s = df_filtrado.resample("D", on="Date").size()
    idx = pd.date_range(s.index.min(), s.index.max(), freq="D")
    return s.reindex(idx, fill_value=0).rename("y").rename_axis("ds")


def calcular_metricas(y_real, y_prev):
    y_real = np.asarray(y_real, dtype=float)
    y_prev = np.asarray(y_prev, dtype=float)
    mae = mean_absolute_error(y_real, y_prev)
    rmse = np.sqrt(mean_squared_error(y_real, y_prev))
    nao_zero = y_real > 0
    mape = np.mean(np.abs((y_real[nao_zero] - y_prev[nao_zero]) / y_real[nao_zero])) * 100 if nao_zero.any() else np.nan
    denom = np.abs(y_real) + np.abs(y_prev)
    smape = np.mean(np.where(denom == 0, 0, 2 * np.abs(y_real - y_prev) / np.where(denom == 0, 1, denom))) * 100
    return {"MAE": mae, "RMSE": rmse, "MAPE": mape, "sMAPE": smape, "dias_zero": int((~nao_zero).sum())}


def mostrar_metricas(m, titulo=None):
    if titulo:
        st.markdown(f"**{titulo}**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("MAE", f"{m['MAE']:.2f}")
    c2.metric("RMSE", f"{m['RMSE']:.2f}")
    c3.metric("MAPE", f"{m['MAPE']:.2f}%" if not np.isnan(m["MAPE"]) else "N/D")
    c4.metric("sMAPE", f"{m['sMAPE']:.2f}%")
    if m["dias_zero"]:
        st.caption(f"ℹ️ MAPE calculado sem os {m['dias_zero']} dias com zero ocorrências (divisão por zero). "
                   "Prefira MAE/RMSE/sMAPE para crimes raros.")


def grafico_previsao(treino, teste, previsoes, titulo, intervalo=None):
    """previsoes: dict nome -> Series alinhada ao índice de `teste`."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=treino.index, y=treino.values, mode="lines", name="Treino",
                             line=dict(color="#1f77b4", width=1), opacity=0.6))
    fig.add_trace(go.Scatter(x=teste.index, y=teste.values, mode="lines", name="Real (Teste)",
                             line=dict(color="#2ca02c", width=2)))
    cores = ["#d62728", "#ff7f0e", "#9467bd"]
    for cor, (nome, prev) in zip(cores, previsoes.items()):
        fig.add_trace(go.Scatter(x=prev.index, y=prev.values, mode="lines", name=nome,
                                 line=dict(color=cor, width=2, dash="dash")))
    if intervalo is not None:
        lo, hi = intervalo
        fig.add_trace(go.Scatter(x=hi.index, y=hi.values, mode="lines", line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=lo.index, y=lo.values, mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor="rgba(214,39,40,0.15)",
                                 name="Intervalo 80% (Prophet)"))
    fig.update_layout(title=titulo, xaxis_title="Data", yaxis_title="Crimes por dia",
                      hovermode="x unified", height=500)
    return fig


# =====================================================================
# Prophet
# =====================================================================
def rodar_prophet(treino, teste, seasonality_mode, include_holidays):
    from prophet import Prophet

    model = Prophet(seasonality_mode=seasonality_mode, yearly_seasonality=True,
                    weekly_seasonality=True, daily_seasonality=False)
    if include_holidays:
        model.add_country_holidays(country_name="US")

    df_treino = treino.reset_index()  # colunas ds, y
    model.fit(df_treino)

    future = pd.DataFrame({"ds": teste.index})
    forecast = model.predict(future).set_index("ds")
    yhat = forecast["yhat"].clip(lower=0)
    return model, forecast, yhat


# =====================================================================
# Random Forest
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
    """Lags e médias móveis usando SOMENTE o passado (shift(1) antes do rolling)."""
    f = pd.DataFrame(index=y.index)
    for lag in range(1, lags_dias + 1):
        f[f"lag_{lag}d"] = y.shift(lag)
    passado = y.shift(1)
    f["rolling_mean_7d"] = passado.rolling(7).mean()
    f["rolling_mean_30d"] = passado.rolling(30).mean()
    f["rolling_std_7d"] = passado.rolling(7).std()
    return f


def rodar_random_forest(treino, teste, n_estimators, lags_dias, modo_recursivo):
    anos = range(treino.index.min().year, teste.index.max().year + 1)
    serie_total = pd.concat([treino, teste])
    cal = features_calendario(serie_total.index, anos)

    # ---- treino ----
    X_treino = pd.concat([cal.loc[treino.index], features_lags(treino, lags_dias)], axis=1).dropna()
    y_treino = treino.loc[X_treino.index]

    model = RandomForestRegressor(n_estimators=n_estimators, random_state=42, n_jobs=-1, min_samples_leaf=2)
    model.fit(X_treino, y_treino)
    colunas = list(X_treino.columns)

    # ---- teste ----
    if not modo_recursivo:
        # 1 passo à frente: lags vêm dos valores REAIS dos dias anteriores
        lags_total = features_lags(serie_total, lags_dias)
        X_teste = pd.concat([cal.loc[teste.index], lags_total.loc[teste.index]], axis=1)[colunas]
        y_prev = pd.Series(model.predict(X_teste), index=teste.index)
    else:
        # Recursivo: o histórico do período de teste são as PRÓPRIAS previsões
        hist = serie_total.astype(float).copy()
        hist.loc[teste.index] = np.nan
        valores = hist.values
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
    return model, y_prev.clip(lower=0), importancias


# =====================================================================
# Página
# =====================================================================
def main():
    st.title("🔮 Predição Diária de Crimes")
    if st.button("← Voltar ao Início"):
        st.switch_page("app.py")

    df = load_all()
    if df.empty:
        st.error("❌ Não foi possível carregar os dados. Verifique se os arquivos estão na pasta 'data_splits'.")
        return

    # ---------------- Sidebar ----------------
    st.sidebar.header("🤖 Modelo")
    modelo_selecionado = st.sidebar.radio(
        "Selecione:", ["Prophet", "Random Forest", "Comparar os dois"],
        help="Todos usam a mesma série diária, o mesmo treino e o mesmo teste.",
    )

    crime_types = sorted(df["Primary Type"].unique())
    selected_crime = st.sidebar.selectbox(
        "Tipo de Crime", crime_types, index=crime_types.index("THEFT") if "THEFT" in crime_types else 0
    )

    st.sidebar.header("📅 Janela Temporal")
    anos = sorted(int(a) for a in df["Year"].unique())
    if len(anos) < 2:
        st.error("❌ Não há anos suficientes no dataset para treino e teste")
        return

    train_start = st.sidebar.selectbox("Início do Treino", anos[:-1], index=max(0, len(anos) - 4))
    fins_possiveis = [a for a in anos[:-1] if a >= train_start]
    train_end = st.sidebar.selectbox("Fim do Treino", fins_possiveis, index=min(2, len(fins_possiveis) - 1))
    # O teste é sempre o ano imediatamente seguinte ao treino (holdout contíguo).
    # Um intervalo entre treino e teste criaria um "buraco" na série diária.
    test_year = train_end + 1
    if test_year not in anos:
        st.error("❌ Não há ano de teste disponível após o fim do treino.")
        return
    st.sidebar.selectbox("Ano para Teste", [test_year], index=0, disabled=True,
                         help="Sempre o ano seguinte ao fim do treino, para não deixar lacuna na série.")
    train_years = list(range(train_start, train_end + 1))

    usar_prophet = modelo_selecionado in ("Prophet", "Comparar os dois")
    usar_rf = modelo_selecionado in ("Random Forest", "Comparar os dois")

    if usar_prophet:
        st.sidebar.subheader("⚙️ Prophet")
        seasonality_mode = st.sidebar.radio("Modo Sazonalidade", ["multiplicative", "additive"])
        include_holidays = st.sidebar.checkbox("Incluir Feriados (EUA)", value=True)

    if usar_rf:
        st.sidebar.subheader("🌲 Random Forest")
        n_estimators = st.sidebar.slider("Número de Árvores", 50, 500, 200, step=50)
        lags_dias = st.sidebar.slider("Lags (dias históricos)", 7, 60, 14)
        modo_rf = st.sidebar.radio(
            "Modo de previsão",
            ["Recursivo (multi-passo, comparável ao Prophet)", "1 passo à frente (usa valores reais do dia anterior)"],
            help="No modo recursivo o modelo prevê o ano inteiro sem ver os valores reais do teste, "
                 "como o Prophet. No modo 1 passo ele sempre conhece o dia anterior real, "
                 "o que gera erros menores mas não é uma previsão de longo prazo.",
        )
        modo_recursivo = modo_rf.startswith("Recursivo")

    # ---------------- Dados ----------------
    df_filtered = df[(df["Primary Type"] == selected_crime) & df["Year"].isin(train_years + [test_year])]
    if df_filtered.empty:
        st.error("❌ Não há dados para o crime e anos selecionados!")
        return

    serie = serie_diaria(df_filtered)
    treino = serie[(serie.index.year >= train_start) & (serie.index.year <= train_end)]
    teste = serie[serie.index.year == test_year]

    if len(treino) < 60 or teste.empty:
        st.error("❌ Dados insuficientes para treino e teste com o período selecionado.")
        return

    st.sidebar.success(f"✅ {len(df_filtered):,} registros de {selected_crime}")
    st.sidebar.write(f"📊 Treino: {treino.index.min():%d/%m/%Y} a {treino.index.max():%d/%m/%Y} ({len(treino)} dias)")
    st.sidebar.write(f"🎯 Teste: {teste.index.min():%d/%m/%Y} a {teste.index.max():%d/%m/%Y} ({len(teste)} dias)")

    # ---------------- Execução ----------------
    if not st.button(f"🚀 Executar: {modelo_selecionado}", type="primary"):
        st.markdown(f"""
        ### 📋 Configuração atual
        - **Crime:** {selected_crime}
        - **Treino:** {min(train_years)} a {max(train_years)} ({len(treino)} dias)
        - **Teste:** {test_year} ({len(teste)} dias)

        Ambos os modelos recebem a **mesma série diária** (dias sem ocorrência contam como 0)
        e são avaliados nos **mesmos dias de teste**, com MAE, RMSE, MAPE e sMAPE.

        **Prophet**: modelo aditivo/multiplicativo com tendência, sazonalidade semanal e anual e feriados.
        Prevê o ano de teste inteiro de uma vez (multi-passo).

        **Random Forest**: usa calendário (dia da semana, mês, feriado, estação...), lags e médias
        móveis calculados **apenas com o passado**. No modo recursivo também prevê o ano inteiro
        reaproveitando as próprias previsões como histórico.
        """)
        return

    previsoes, metricas = {}, {}
    intervalo = None
    modelo_prophet = forecast_prophet = None
    importancias = None

    if usar_prophet:
        with st.spinner("Treinando Prophet..."):
            try:
                modelo_prophet, forecast_prophet, yhat = rodar_prophet(treino, teste, seasonality_mode, include_holidays)
                previsoes["Prophet"] = yhat
                metricas["Prophet"] = calcular_metricas(teste.values, yhat.values)
                intervalo = (forecast_prophet["yhat_lower"].clip(lower=0), forecast_prophet["yhat_upper"])
            except ImportError:
                st.error("❌ Biblioteca Prophet não instalada. Execute: pip install prophet")
            except Exception as e:
                st.error(f"❌ Erro no Prophet: {e}")

    if usar_rf:
        with st.spinner("Treinando Random Forest..."):
            try:
                rotulo = "Random Forest (recursivo)" if modo_recursivo else "Random Forest (1 passo)"
                _, yhat_rf, importancias = rodar_random_forest(treino, teste, n_estimators, lags_dias, modo_recursivo)
                previsoes[rotulo] = yhat_rf
                metricas[rotulo] = calcular_metricas(teste.values, yhat_rf.values)
            except Exception as e:
                st.error(f"❌ Erro no Random Forest: {e}")

    if not previsoes:
        return

    st.success("✅ Previsão concluída!")

    # ---------------- Métricas ----------------
    st.subheader("📏 Métricas no período de teste")
    if len(metricas) == 1:
        mostrar_metricas(next(iter(metricas.values())))
    else:
        tabela = pd.DataFrame(metricas).T[["MAE", "RMSE", "MAPE", "sMAPE"]].round(2)
        st.dataframe(tabela, width="stretch")
        melhor = tabela["MAE"].idxmin()
        st.info(f"🏆 Menor MAE: **{melhor}**")
        for nome, m in metricas.items():
            if m["dias_zero"]:
                st.caption(f"ℹ️ {m['dias_zero']} dias com zero ocorrências foram ignorados no MAPE.")
                break

    if usar_rf and not modo_recursivo and usar_prophet:
        st.warning("⚠️ O Random Forest em modo *1 passo* conhece o valor real do dia anterior; "
                   "o Prophet não. Para comparação justa use o modo recursivo.")

    # ---------------- Gráfico ----------------
    st.subheader("📊 Previsão vs Real")
    fig = grafico_previsao(treino, teste, previsoes,
                           f"{selected_crime} — previsão diária para {test_year}", intervalo)
    st.plotly_chart(fig, width="stretch")

    # Agregado mensal: facilita enxergar viés sistemático
    st.subheader("📅 Totais mensais (real × previsto)")
    mensal = pd.DataFrame({"Real": teste.resample("MS").sum()})
    for nome, prev in previsoes.items():
        mensal[nome] = prev.resample("MS").sum().round(0)
    mensal.index = mensal.index.strftime("%b/%Y")
    st.dataframe(mensal.astype(int), width="stretch")

    # ---------------- Detalhes por modelo ----------------
    if modelo_prophet is not None:
        with st.expander("🔍 Componentes do Prophet (tendência, sazonalidades, feriados)"):
            try:
                hist_e_futuro = pd.concat([treino.reset_index()[["ds"]], pd.DataFrame({"ds": teste.index})])
                fc_completo = modelo_prophet.predict(hist_e_futuro)
                st.pyplot(modelo_prophet.plot_components(fc_completo))
            except Exception as e:
                st.info(f"Visualização de componentes não disponível: {e}")

    if importancias is not None:
        with st.expander("🌲 Importância das features do Random Forest (Top 15)"):
            top = importancias.head(15)[::-1]
            fig_imp = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h"))
            fig_imp.update_layout(xaxis_title="Importância", height=450)
            st.plotly_chart(fig_imp, width="stretch")

    with st.expander("📈 Amostra de previsões diárias (primeiros 15 dias)"):
        amostra = pd.DataFrame({"Real": teste})
        for nome, prev in previsoes.items():
            amostra[nome] = prev.round(1)
            amostra[f"Erro abs. {nome}"] = (teste - prev).abs().round(1)
        amostra.index = amostra.index.strftime("%d/%m/%Y")
        st.dataframe(amostra.head(15), width="stretch")

    st.markdown("---")
    st.markdown("**Módulo de Predição - Chicago Crime Analytics**")


if __name__ == "__main__":
    main()
