# pages/03_predicao_crimes.py - Previsão diária de crimes (Prophet x Random Forest)
#
# Esta página é só INTERFACE. Toda a lógica de previsão vive em forecasting.py,
# para que possa ser testada (tests/) e executada sem o dashboard
# (experiments/run_rolling_origin.py).
#
# Três coisas que a interface faz questão de mostrar, e por quê:
#   * Linhas de base (naive sazonal e climatologia por dia da semana) aparecem
#     sempre. Sem um comparador trivial não se sabe se o modelo entrega algo.
#   * ME (erro médio com sinal) ao lado de MAE/RMSE. É a métrica que denuncia
#     viés de nível — um modelo pode errar o patamar inteiro sem que MAE ou MAPE
#     digam de onde vem o erro.
#   * Modo recursivo e modo de 1 passo à frente nunca se misturam na mesma
#     comparação sem aviso: são horizontes diferentes.
import sys
import os
import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Configuração da página DEVE SER SEMPRE A PRIMEIRA COISA
st.set_page_config(page_title="Predição Crimes", page_icon="🔮", layout="wide")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_data, ANO_MIN, ANO_MAX  # noqa: E402
import forecasting as fc  # noqa: E402

# Silencia apenas o ruído conhecido do cmdstanpy/Prophet durante o ajuste.
# filterwarnings("ignore") global escondia avisos de depreciação que antecipam
# quebras em produção.
warnings.filterwarnings("ignore", category=FutureWarning, module="prophet")
warnings.filterwarnings("ignore", message=".*Importing plotly failed.*")

COLUNAS = ["Date", "Primary Type", "Year"]  # o necessário para a série diária


# =====================================================================
# Execução dos modelos (com cache: um clique repetido é instantâneo)
# =====================================================================
@st.cache_data(show_spinner=False)
def _series(crime, train_start, train_end, test_year):
    """Série diária de treino e de teste para o recorte pedido."""
    df = load_data((train_start, test_year), colunas=COLUNAS)
    sub = df[(df["Primary Type"] == crime) & df["Year"].between(train_start, test_year)]
    if sub.empty:
        return None, None
    serie = fc.serie_diaria(sub)
    treino = serie[(serie.index.year >= train_start) & (serie.index.year <= train_end)]
    teste = serie[serie.index.year == test_year]
    return treino, teste


@st.cache_data(show_spinner=False)
def _prever_prophet(crime, t0, t1, ty, seasonality_mode, include_holidays, cps):
    treino, teste = _series(crime, t0, t1, ty)
    modelo, forecast, yhat = fc.rodar_prophet(treino, teste, seasonality_mode,
                                              include_holidays, cps)
    # O modelo em si não é serializável pelo cache; devolvemos só o que a tela usa.
    componentes = forecast[["trend", "yhat", "yhat_lower", "yhat_upper"]]
    return yhat, componentes


@st.cache_data(show_spinner=False)
def _prever_rf(crime, t0, t1, ty, n_estimators, lags_dias, modo_recursivo):
    treino, teste = _series(crime, t0, t1, ty)
    return fc.rodar_random_forest(treino, teste, n_estimators, lags_dias, modo_recursivo)


# =====================================================================
# Apresentação
# =====================================================================
def tabela_metricas(metricas):
    linhas = {}
    for nome, m in metricas.items():
        linhas[nome] = {"MAE": m["MAE"], "RMSE": m["RMSE"], "ME (viés)": m["ME"],
                        "MAPE (%)": m["MAPE"], "sMAPE (%)": m["sMAPE"]}
    return pd.DataFrame(linhas).T.round(2)


def grafico_previsao(treino, teste, previsoes, titulo, intervalo=None, cores=None):
    fig = go.Figure()
    # Só os últimos 120 dias de treino: o ano de teste é o que interessa ler.
    cauda = treino.iloc[-120:]
    fig.add_trace(go.Scatter(x=cauda.index, y=cauda.values, mode="lines", name="Treino (fim)",
                             line=dict(color="#9e9e9e", width=1), opacity=0.7))
    fig.add_trace(go.Scatter(x=teste.index, y=teste.values, mode="lines", name="Observado (teste)",
                             line=dict(color="#444444", width=1.4), opacity=0.8))
    padrao = {"Prophet": "#1f78b4", "Random Forest (recursivo)": "#e31a1c",
              "Random Forest (1 passo)": "#fb9a99", "Naive sazonal": "#b0b0b0",
              "Climatologia (dia da semana)": "#7f7f7f"}
    cores = cores or padrao
    for nome, prev in previsoes.items():
        tracejado = "dot" if nome in ("Naive sazonal", "Climatologia (dia da semana)") else "dash"
        fig.add_trace(go.Scatter(x=prev.index, y=prev.values, mode="lines", name=nome,
                                 line=dict(color=cores.get(nome, "#9467bd"), width=2, dash=tracejado)))
    if intervalo is not None:
        lo, hi = intervalo
        fig.add_trace(go.Scatter(x=hi.index, y=hi.values, mode="lines", line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=lo.index, y=lo.values, mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor="rgba(31,120,180,0.15)",
                                 name="Intervalo 80% (Prophet)"))
    fig.update_layout(title=titulo, xaxis_title="Data", yaxis_title="Crimes por dia",
                      hovermode="x unified", height=520, legend=dict(orientation="h", y=-0.18))
    return fig


def main():
    st.title("🔮 Predição Diária de Crimes")
    if st.button("← Voltar ao Início"):
        st.switch_page("app.py")

    # ---------------- Sidebar: recorte ----------------
    st.sidebar.header("📅 Janela Temporal")
    anos = list(range(ANO_MIN, ANO_MAX + 1))
    train_start = st.sidebar.selectbox("Início do Treino", anos[:-1],
                                       index=max(0, len(anos) - 5))
    fins_possiveis = [a for a in anos[:-1] if a >= train_start]
    train_end = st.sidebar.selectbox("Fim do Treino", fins_possiveis,
                                     index=min(3, len(fins_possiveis) - 1))
    # O teste é sempre o ano imediatamente seguinte ao treino (holdout contíguo).
    # Um intervalo entre treino e teste criaria um "buraco" na série diária.
    test_year = train_end + 1
    if test_year > ANO_MAX:
        st.error("❌ Não há ano de teste disponível após o fim do treino.")
        return
    st.sidebar.selectbox("Ano para Teste", [test_year], index=0, disabled=True,
                         help="Sempre o ano seguinte ao fim do treino, para não deixar lacuna na série.")

    # Só os anos do recorte saem do disco (ver data_loader.load_data).
    df = load_data((train_start, test_year), colunas=COLUNAS)
    if df.empty:
        st.error("❌ Não foi possível carregar os dados. Verifique a pasta 'data/processed'.")
        return

    crime_types = sorted(df["Primary Type"].unique())
    selected_crime = st.sidebar.selectbox(
        "Tipo de Crime", crime_types,
        index=crime_types.index("THEFT") if "THEFT" in crime_types else 0,
    )

    st.sidebar.header("🤖 Modelos")
    usar_prophet = st.sidebar.checkbox("Prophet", value=True)
    usar_rf = st.sidebar.checkbox("Random Forest", value=True)
    st.sidebar.caption("As linhas de base (naive sazonal e climatologia) entram sempre: "
                       "são a régua para saber se o modelo entrega algo.")

    if usar_prophet:
        st.sidebar.subheader("⚙️ Prophet")
        seasonality_mode = st.sidebar.radio("Modo Sazonalidade", ["multiplicative", "additive"])
        include_holidays = st.sidebar.checkbox("Incluir Feriados (EUA)", value=True,
                                              help="Janela de 0 dias: o efeito é estimado só no "
                                                   "próprio dia do feriado.")
        cps = st.sidebar.select_slider(
            "Flexibilidade da tendência (changepoint_prior_scale)",
            options=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
            value=fc.PROPHET_CPS_PADRAO,
            help="Menor = tendência mais rígida, menos extrapolada. Não existe valor "
                 "universalmente melhor: medido em 35 origens, 0.001 reduz muito o erro "
                 "quando a quebra de nível ocorre no fim do treino (furtos 2021: MAPE de "
                 "54,5% para 17,3%) e o aumenta quando a tendência recente era informativa "
                 "(furto de veículo 2024: de 28,7% para 65,3%). É uma troca entre dois "
                 "modos de falha, não um conserto: no agregado melhora em 16 das 35 origens "
                 "e em 4 das 10 de quebra, com ganho mediano de -0,05 p.p.",
        )

    if usar_rf:
        st.sidebar.subheader("🌲 Random Forest")
        n_estimators = st.sidebar.slider("Número de Árvores", 50, 500, 200, step=50)
        lags_dias = st.sidebar.slider("Lags (dias históricos)", 7, 60, 14)
        modo_rf = st.sidebar.radio(
            "Modo de previsão",
            ["Recursivo (multi-passo, comparável ao Prophet)",
             "1 passo à frente (usa valores reais do dia anterior)"],
            help="No modo recursivo o modelo prevê o ano inteiro sem ver os valores reais do "
                 "teste, como o Prophet. No modo 1 passo ele sempre conhece o dia anterior "
                 "real, o que gera erros menores mas não é uma previsão de longo prazo.",
        )
        modo_recursivo = modo_rf.startswith("Recursivo")

    # ---------------- Série ----------------
    treino, teste = _series(selected_crime, train_start, train_end, test_year)
    if treino is None or len(treino) < 60 or teste is None or teste.empty:
        st.error("❌ Dados insuficientes para treino e teste com o período selecionado.")
        return

    n_registros = int(treino.sum() + teste.sum())
    st.sidebar.success(f"✅ {n_registros:,} registros de {selected_crime}")
    st.sidebar.write(f"📊 Treino: {treino.index.min():%d/%m/%Y} a {treino.index.max():%d/%m/%Y} "
                     f"({len(treino)} dias, média {treino.mean():.1f}/dia)")
    st.sidebar.write(f"🎯 Teste: {teste.index.min():%d/%m/%Y} a {teste.index.max():%d/%m/%Y} "
                     f"({len(teste)} dias, média {teste.mean():.1f}/dia)")

    delta_nivel = (teste.mean() / treino.mean() - 1) * 100
    if abs(delta_nivel) >= 15:
        st.warning(
            f"⚠️ **Quebra de regime neste recorte:** o nível médio do teste está "
            f"{delta_nivel:+.0f}% em relação ao treino. Modelos que extrapolam tendência "
            f"(Prophet) tendem a falhar aqui; modelos ancorados no nível recente "
            f"(Random Forest recursivo, climatologia) degradam menos."
        )

    if not st.button(f"🚀 Executar previsão para {test_year}", type="primary"):
        st.markdown(f"""
        ### 📋 Configuração atual
        - **Crime:** {selected_crime}
        - **Treino:** {train_start} a {train_end} ({len(treino)} dias)
        - **Teste:** {test_year} ({len(teste)} dias)
        - **Variação de nível treino → teste:** {delta_nivel:+.1f}%

        Todos os modelos recebem a **mesma série diária** (dias sem ocorrência contam como 0)
        e são avaliados nos **mesmos dias de teste**.

        **Prophet** e **Random Forest recursivo** preveem o ano de teste inteiro sem ver
        nenhum valor observado do período — são os dois comparáveis entre si.
        **Random Forest 1 passo** conhece o dia anterior real: erro menor, outro problema.
        **Naive sazonal** repete a última semana do treino; **climatologia** usa a média por
        dia da semana do último ano de treino.
        """)
        return

    # ---------------- Execução ----------------
    previsoes, metricas = {}, {}
    intervalo = None
    componentes = None
    importancias = None

    # Linhas de base: sempre, e são baratas.
    previsoes["Naive sazonal"] = fc.naive_sazonal(treino, teste)
    previsoes["Climatologia (dia da semana)"] = fc.climatologia(treino, teste)

    if usar_prophet:
        with st.spinner("Ajustando Prophet..."):
            try:
                yhat, componentes = _prever_prophet(selected_crime, train_start, train_end,
                                                    test_year, seasonality_mode,
                                                    include_holidays, cps)
                previsoes["Prophet"] = yhat
                intervalo = (componentes["yhat_lower"].clip(lower=0), componentes["yhat_upper"])
            except ImportError:
                st.error("❌ Biblioteca Prophet não instalada. Execute: pip install prophet")
            except Exception as e:
                st.error(f"❌ Erro no Prophet: {e}")
                st.exception(e)

    if usar_rf:
        with st.spinner("Treinando Random Forest (o modo recursivo prevê dia a dia)..."):
            try:
                rotulo = ("Random Forest (recursivo)" if modo_recursivo
                          else "Random Forest (1 passo)")
                yhat_rf, importancias = _prever_rf(selected_crime, train_start, train_end,
                                                   test_year, n_estimators, lags_dias,
                                                   modo_recursivo)
                previsoes[rotulo] = yhat_rf
            except Exception as e:
                st.error(f"❌ Erro no Random Forest: {e}")
                st.exception(e)

    for nome, prev in previsoes.items():
        metricas[nome] = fc.calcular_metricas(teste.values, prev.values)

    st.success("✅ Previsão concluída!")

    # ---------------- Métricas ----------------
    st.subheader("📏 Métricas no período de teste")
    tabela = tabela_metricas(metricas)
    st.dataframe(tabela, width="stretch")

    multi_passo = [n for n in metricas if n not in ("Random Forest (1 passo)",)]
    melhor = tabela.loc[multi_passo, "MAE"].idxmin()
    st.info(f"🏆 Menor MAE entre os modelos de horizonte anual: **{melhor}**")

    base_mae = min(metricas["Naive sazonal"]["MAE"],
                   metricas["Climatologia (dia da semana)"]["MAE"])
    for nome in ("Prophet", "Random Forest (recursivo)"):
        if nome in metricas:
            ganho = (1 - metricas[nome]["MAE"] / base_mae) * 100
            if ganho <= 0:
                st.error(f"❌ **{nome}** não supera a melhor linha de base "
                         f"(MAE {metricas[nome]['MAE']:.2f} contra {base_mae:.2f}). "
                         f"Nesse recorte o modelo não entrega ganho.")
            else:
                st.caption(f"ℹ️ {nome}: {ganho:.0f}% de redução de MAE sobre a melhor linha de base.")

    # Viés: a leitura que MAE e MAPE escondem
    vies = {n: m["ME"] for n, m in metricas.items()}
    pior = max(vies, key=lambda n: abs(vies[n]))
    if abs(vies[pior]) > 0.4 * metricas[pior]["MAE"]:
        st.warning(f"⚠️ **{pior}** tem viés sistemático de {vies[pior]:+.1f} ocorrências/dia "
                   f"contra um MAE de {metricas[pior]['MAE']:.1f} — a maior parte do erro é "
                   f"erro de patamar, não de sazonalidade.")

    if usar_rf and usar_prophet and not modo_recursivo:
        st.warning("⚠️ O Random Forest em modo *1 passo* conhece o valor real do dia anterior; "
                   "o Prophet não. Para comparação justa use o modo recursivo.")

    zeros = next((m["dias_zero"] for m in metricas.values() if m["dias_zero"]), 0)
    if zeros:
        st.caption(f"ℹ️ MAPE calculado sem os {zeros} dias com zero ocorrências (divisão por "
                   "zero). Prefira MAE/RMSE/sMAPE para crimes raros.")

    # ---------------- Gráfico ----------------
    st.subheader("📊 Previsão vs Observado")
    st.plotly_chart(
        grafico_previsao(treino, teste, previsoes,
                         f"{selected_crime} — previsão diária para {test_year}", intervalo),
        width="stretch",
    )

    # Agregado mensal: facilita enxergar viés sistemático
    st.subheader("📅 Totais mensais (observado × previsto)")
    mensal = pd.DataFrame({"Observado": teste.resample("MS").sum()})
    for nome, prev in previsoes.items():
        mensal[nome] = prev.resample("MS").sum().round(0)
    mensal.index = mensal.index.strftime("%b/%Y")
    st.dataframe(mensal.astype(int), width="stretch")

    # ---------------- Detalhes por modelo ----------------
    if componentes is not None:
        with st.expander("🔍 Tendência estimada pelo Prophet no período de teste"):
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(x=componentes.index, y=componentes["trend"],
                                       mode="lines", name="Tendência",
                                       line=dict(color="#1f78b4", width=2)))
            fig_t.add_hline(y=float(treino.mean()), line_dash="dot", line_color="#9e9e9e",
                            annotation_text="média diária do treino")
            fig_t.update_layout(height=320, yaxis_title="Crimes por dia",
                                title="A tendência é extrapolada a partir da taxa estimada no "
                                      "fim do treino")
            st.plotly_chart(fig_t, width="stretch")
            st.caption("Se esta curva se afasta muito da média do treino ao longo do ano de "
                       "teste, a previsão está dominada por extrapolação de tendência. "
                       "Reduza a flexibilidade da tendência na barra lateral.")

    if importancias is not None:
        with st.expander("🌲 Importância das features do Random Forest (Top 15)"):
            top = importancias.head(15)[::-1]
            fig_imp = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h"))
            fig_imp.update_layout(xaxis_title="Importância", height=450)
            st.plotly_chart(fig_imp, width="stretch")

    with st.expander("📈 Amostra de previsões diárias (primeiros 15 dias)"):
        amostra = pd.DataFrame({"Observado": teste})
        for nome, prev in previsoes.items():
            amostra[nome] = prev.round(1)
        amostra.index = amostra.index.strftime("%d/%m/%Y")
        st.dataframe(amostra.head(15), width="stretch")

    st.markdown("---")
    st.markdown("**Módulo de Predição - Chicago Crime Analytics**")


if __name__ == "__main__":
    main()
