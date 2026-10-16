# pages/02_analise_exploratoria.py - Análise exploratória da série temporal
import sys
import os
import warnings

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configuração da página DEVE SER SEMPRE A PRIMEIRA COISA
st.set_page_config(page_title="Análise Exploratória - Crimes Chicago", page_icon="📈", layout="wide")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_all  # noqa: E402

warnings.filterwarnings("ignore")

NOMES_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
DIAS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DIAS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def prepare_temporal_data(df, granularity):
    """Agrega a contagem de crimes por dia, mês ou ano.

    Períodos sem ocorrências entram com y = 0, para que médias e
    estatísticas não fiquem infladas em crimes raros.
    """
    if df.empty:
        return pd.DataFrame(columns=["ds", "y"])

    freq = {"Diária": "D", "Mensal": "MS", "Anual": "YS"}[granularity]
    serie = df.resample(freq, on="Date").size()
    temporal = serie.rename("y").rename_axis("ds").reset_index()
    return temporal.sort_values("ds")


def main():
    st.title("📈 Análise Exploratória dos Padrões de Crimes em Chicago")
    st.markdown("Explore padrões temporais, sazonalidade e tendências dos crimes ao longo do tempo.")

    if st.button("← Voltar para Página Inicial"):
        st.switch_page("app.py")

    df = load_all()
    if df.empty:
        st.error("❌ Não foi possível carregar os dados. Verifique se os arquivos estão na pasta 'data/processed'.")
        return

    # ---------------- Controles ----------------
    st.sidebar.header("🎯 Controles de Análise")

    crime_types = sorted(df["Primary Type"].unique())
    padrao = [c for c in ("THEFT", "BATTERY", "ASSAULT") if c in crime_types] or crime_types[:3]
    selected_crimes = st.sidebar.multiselect("Tipos de Crime:", options=crime_types, default=padrao)

    available_years = sorted(int(a) for a in df["Year"].unique())
    selected_years = st.sidebar.multiselect("Anos:", options=available_years, default=available_years[-3:])

    analysis_granularity = st.sidebar.radio("Agregação Temporal:", ["Diária", "Mensal", "Anual"], index=1)

    if not selected_crimes or not selected_years:
        st.warning("⚠️ Selecione pelo menos um tipo de crime e um ano.")
        return

    df_filtered = df[df["Primary Type"].isin(selected_crimes) & df["Year"].isin(selected_years)]
    st.sidebar.info(f"📊 Registros filtrados: {len(df_filtered):,}")

    if df_filtered.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        return

    temporal_data = prepare_temporal_data(df_filtered, analysis_granularity)
    daily_data = prepare_temporal_data(df_filtered, "Diária")

    tab1, tab2, tab3 = st.tabs(["📊 Série Temporal", "📈 Estatísticas", "🔍 Padrões"])

    # ---------------- Série temporal ----------------
    with tab1:
        st.subheader("Análise da Série Temporal")
        col1, col2 = st.columns([2, 1])

        with col1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=temporal_data["ds"], y=temporal_data["y"],
                mode="lines+markers" if len(temporal_data) < 400 else "lines",
                name="Crimes", line=dict(color="#1f77b4", width=2),
            ))
            # Tendência suavizada (média móvel) ajuda a ler séries diárias ruidosas
            if analysis_granularity == "Diária" and len(temporal_data) > 30:
                fig.add_trace(go.Scatter(
                    x=temporal_data["ds"], y=temporal_data["y"].rolling(30, center=True).mean(),
                    mode="lines", name="Média móvel 30 dias", line=dict(color="#d62728", width=2),
                ))
            fig.update_layout(
                title=f"Série Temporal - {', '.join(selected_crimes)}",
                xaxis_title="Data",
                yaxis_title=f"Número de Crimes ({analysis_granularity.lower()})",
                height=400,
            )
            st.plotly_chart(fig, width="stretch")

        with col2:
            st.subheader("📈 Métricas")
            st.metric("Total de Crimes", f"{int(temporal_data['y'].sum()):,}")
            st.metric(f"Média {analysis_granularity}", f"{temporal_data['y'].mean():.1f}")
            st.metric("Máximo", f"{int(temporal_data['y'].max()):,}")
            if len(temporal_data) > 1:
                primeiro, ultimo = temporal_data["y"].iloc[0], temporal_data["y"].iloc[-1]
                if primeiro > 0:
                    st.metric("Variação (1º → último período)", f"{(ultimo / primeiro - 1) * 100:+.1f}%")

    # ---------------- Estatísticas ----------------
    with tab2:
        st.subheader("Estatísticas Descritivas (por dia)")
        col1, col2 = st.columns(2)

        with col1:
            stats_df = pd.DataFrame({
                "Métrica": ["Total", "Média", "Mediana", "Desvio Padrão", "Máximo", "Mínimo", "Dias analisados"],
                "Valor": [
                    f"{int(daily_data['y'].sum()):,}",
                    f"{daily_data['y'].mean():.2f}",
                    f"{daily_data['y'].median():.2f}",
                    f"{daily_data['y'].std():.2f}",
                    f"{int(daily_data['y'].max()):,}",
                    f"{int(daily_data['y'].min()):,}",
                    f"{len(daily_data):,}",
                ],
            })
            st.dataframe(stats_df, width="stretch", hide_index=True)

        with col2:
            fig_hist = px.histogram(
                daily_data, x="y", nbins=30,
                title="Distribuição de Crimes por Dia",
                labels={"y": "Número de Crimes"},
                color_discrete_sequence=["#1f77b4"],
            )
            fig_hist.update_layout(yaxis_title="Frequência (dias)")
            st.plotly_chart(fig_hist, width="stretch")

    # ---------------- Padrões ----------------
    with tab3:
        st.subheader("Análise de Padrões")
        daily = daily_data.copy()
        daily["dia_semana"] = daily["ds"].dt.day_name()
        daily["mes"] = daily["ds"].dt.month

        col1, col2 = st.columns(2)

        with col1:
            media_semanal = daily.groupby("dia_semana")["y"].mean().reindex(DIAS_EN)
            fig_semanal = px.bar(
                x=DIAS_PT, y=media_semanal.values,
                title="Média de Crimes por Dia da Semana",
                labels={"x": "Dia da Semana", "y": "Média de Crimes/dia"},
            )
            st.plotly_chart(fig_semanal, width="stretch")

        with col2:
            # reindex(1..12) garante 12 valores mesmo se faltarem meses nos dados
            media_mensal = daily.groupby("mes")["y"].mean().reindex(range(1, 13))
            fig_mensal = px.line(
                x=NOMES_MESES, y=media_mensal.values, markers=True,
                title="Média de Crimes por Mês",
                labels={"x": "Mês", "y": "Média de Crimes/dia"},
            )
            st.plotly_chart(fig_mensal, width="stretch")

        # Heatmap ano x mês: mostra tendência e sazonalidade de uma vez
        if len(selected_years) > 1:
            st.subheader("🗓️ Mapa de calor Ano × Mês")
            mensal = prepare_temporal_data(df_filtered, "Mensal")
            pivot = mensal.assign(ano=mensal["ds"].dt.year, mes=mensal["ds"].dt.month) \
                          .pivot(index="ano", columns="mes", values="y").reindex(columns=range(1, 13))
            pivot.columns = NOMES_MESES
            fig_heat = px.imshow(
                pivot, aspect="auto", color_continuous_scale="Reds",
                labels=dict(x="Mês", y="Ano", color="Crimes"),
            )
            st.plotly_chart(fig_heat, width="stretch")

        # Outliers (regra do IQR, nos dois lados)
        st.subheader("🚨 Análise de Valores Atípicos (dias)")
        q1, q3 = daily["y"].quantile([0.25, 0.75])
        iqr = q3 - q1
        lim_sup, lim_inf = q3 + 1.5 * iqr, q1 - 1.5 * iqr
        outliers_sup = daily[daily["y"] > lim_sup]
        outliers_inf = daily[daily["y"] < lim_inf]

        col3, col4 = st.columns(2)
        with col3:
            st.metric("Dias atípicos (acima)", len(outliers_sup))
            st.metric("Dias atípicos (abaixo)", len(outliers_inf))
            st.caption(f"Limites IQR: {max(lim_inf, 0):.1f} a {lim_sup:.1f} crimes/dia")
        with col4:
            if not outliers_sup.empty:
                st.markdown("**Top 5 dias com mais crimes:**")
                top = outliers_sup.nlargest(5, "y")[["ds", "y"]].copy()
                top["ds"] = top["ds"].dt.strftime("%d/%m/%Y (%a)")
                st.dataframe(top.rename(columns={"ds": "Data", "y": "Crimes"}), hide_index=True, width="stretch")
            else:
                st.info("Nenhum dia atípico acima do limite superior.")

    # ---------------- Recomendações ----------------
    st.markdown("---")
    st.subheader("🚀 Recomendações para Modelagem Preditiva")
    col1, col2, col3 = st.columns(3)
    col1.info("**📅 Sazonalidade**\n- Padrão semanal bem definido\n- Considerar feriados\n- Sazonalidade anual (verão > inverno)")
    col2.info("**⚙️ Configurações Prophet**\n- seasonality_mode='multiplicative'\n- weekly_seasonality=True\n- yearly_seasonality=True")
    col3.info("**📊 Validação**\n- Holdout temporal (treino → teste)\n- Métricas: MAE, RMSE, MAPE\n- Comparar previsão multi-passo entre modelos")

    st.markdown("---")
    st.markdown("**Módulo de Análise Exploratória - Chicago Crime Analytics**")


if __name__ == "__main__":
    main()
