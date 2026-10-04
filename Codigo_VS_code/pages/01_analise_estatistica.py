# pages/01_analise_estatistica.py - Navegação e filtragem do banco de dados
import sys
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# Configuração da página DEVE SER SEMPRE A PRIMEIRA COISA
st.set_page_config(page_title="Análise Estatística - Crimes Chicago", page_icon="📊", layout="wide")

# Permite importar data_loader.py da pasta raiz do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_all  # noqa: E402

DIAS_SEMANA = {
    "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta", "Thursday": "Quinta",
    "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo",
}

PERIODOS_DIA = {
    "Todo o dia (00:00-23:59)": (0, 23),
    "Madrugada (00:00-05:59)": (0, 5),
    "Manhã (06:00-11:59)": (6, 11),
    "Tarde (12:00-17:59)": (12, 17),
    "Noite (18:00-23:59)": (18, 23),
}


def main():
    st.title("📊 Análise Estatística")
    st.markdown("Navegue e filtre o banco de dados completo de crimes de Chicago")

    if st.button("← Voltar para Página Inicial"):
        st.switch_page("app.py")

    df_full = load_all()
    if df_full.empty:
        st.error("❌ Não foi possível carregar os dados. Verifique se os arquivos estão na pasta 'data_splits'.")
        return

    # ---------------- Filtros ----------------
    st.sidebar.header("🔧 Filtros para Análise")

    anos_disponiveis = sorted(int(a) for a in df_full["Year"].unique())
    anos_padrao = [a for a in (2022, 2023, 2024) if a in anos_disponiveis] or anos_disponiveis[-1:]
    anos_selecionados = st.sidebar.multiselect(
        "Selecione os anos para análise:", options=anos_disponiveis, default=anos_padrao
    )

    crime_types_full = sorted(df_full["Primary Type"].unique())
    selected_crime = st.sidebar.multiselect(
        "Selecione o tipo de crime:", crime_types_full, default=crime_types_full
    )

    periodo_selecionado = st.sidebar.selectbox("Período do dia:", options=list(PERIODOS_DIA.keys()))

    distritos = None
    if "District" in df_full.columns:
        distritos_disponiveis = sorted(int(d) for d in df_full["District"].dropna().unique())
        distritos = st.sidebar.multiselect(
            "Selecione os distritos:", distritos_disponiveis, default=distritos_disponiveis
        )

    # ---------------- Aplicação dos filtros ----------------
    if not anos_selecionados:
        st.warning("⚠️ Selecione pelo menos um ano na barra lateral.")
        return
    if not selected_crime:
        st.warning("⚠️ Selecione pelo menos um tipo de crime na barra lateral.")
        return

    mask = df_full["Year"].isin(anos_selecionados) & df_full["Primary Type"].isin(selected_crime)

    hora_i, hora_f = PERIODOS_DIA[periodo_selecionado]
    if (hora_i, hora_f) != (0, 23):
        mask &= df_full["Hour"].between(hora_i, hora_f)

    if distritos is not None:
        mask &= df_full["District"].isin(distritos)

    df_filtrado = df_full[mask]

    st.sidebar.info(f"📅 Anos: {', '.join(map(str, sorted(anos_selecionados)))}")

    if df_filtrado.empty:
        st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados. Ajuste os critérios na barra lateral.")
        return

    st.success(f"✅ **{len(df_filtrado):,} registros** encontrados com os filtros aplicados")

    # value_counts em coluna categórica inclui categorias com 0 ocorrências;
    # observed=True / filtro > 0 evita isso.
    contagem_tipos = df_filtrado["Primary Type"].value_counts()
    contagem_tipos = contagem_tipos[contagem_tipos > 0]

    # ---------------- Métricas ----------------
    st.header("📈 Visão Geral dos Dados Selecionados")
    col1, col2, col3, col4 = st.columns(4)

    total_crimes = len(df_filtrado)
    dias_unicos = df_filtrado["Date"].dt.normalize().nunique()

    col1.metric("Total de crimes", f"{total_crimes:,}")
    col2.metric("Média de crimes por dia", f"{total_crimes / dias_unicos:.1f}" if dias_unicos else "N/D")
    if "Arrest" in df_filtrado.columns:
        col3.metric("Taxa de Prisões", f"{df_filtrado['Arrest'].mean() * 100:.1f}%")
    else:
        col3.metric("Taxa de Prisões", "N/D")
    col4.metric("Tipo de crime mais comum", str(contagem_tipos.idxmax()))

    # ---------------- Gráficos ----------------
    st.header("📊 Análises Visuais Rápidas")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribuição por Tipo de Crime")
        top10 = contagem_tipos.head(10)
        fig_pizza = px.pie(
            values=top10.values,
            names=top10.index.astype(str),
            title="Top 10 tipos de crime (participação %)",
        )
        st.plotly_chart(fig_pizza, width="stretch")

    with col2:
        st.subheader("Crimes por Hora do Dia")
        crimes_por_hora = df_filtrado["Hour"].value_counts().reindex(range(24), fill_value=0)
        fig_hora = px.bar(
            x=crimes_por_hora.index,
            y=crimes_por_hora.values,
            title="Distribuição de Crimes por Hora",
            labels={"x": "Hora do Dia", "y": "Número de Crimes"},
        )
        hora_pico = int(crimes_por_hora.idxmax())
        fig_hora.add_annotation(x=hora_pico, y=crimes_por_hora.max(), text=f"Pico: {hora_pico}h", showarrow=True)
        st.plotly_chart(fig_hora, width="stretch")

    # ---------------- Análise detalhada ----------------
    st.header("🔍 Análise Detalhada dos Dados")
    tab1, tab2, tab3 = st.tabs(["📋 Dados Filtrados", "📊 Estatísticas", "📥 Exportar Dados"])

    with tab1:
        st.subheader("Visualização dos Dados Filtrados")
        page_size = 100
        total_pages = max(1, (len(df_filtrado) + page_size - 1) // page_size)
        page = st.number_input("Página", min_value=1, max_value=total_pages, value=1)
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(df_filtrado))
        st.dataframe(df_filtrado.iloc[start_idx:end_idx], width="stretch")
        st.caption(f"Página {page} de {total_pages:,} | Registros {start_idx + 1:,} a {end_idx:,} de {len(df_filtrado):,}")

    with tab2:
        st.subheader("Estatísticas Descritivas")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Distribuição por Tipo de Crime (Top 10):**")
            pct = contagem_tipos / contagem_tipos.sum() * 100
            for crime_type, percentage in pct.head(10).items():
                st.write(f"• {crime_type}: **{percentage:.1f}%**")

            st.write("**Informações Gerais:**")
            st.write(f"• Total de tipos distintos: **{len(contagem_tipos)}**")
            st.write(f"• Dias com ocorrências: **{dias_unicos:,}**")
            if "Domestic" in df_filtrado.columns:
                st.write(f"• Crimes domésticos: **{df_filtrado['Domestic'].mean() * 100:.1f}%**")

        with col2:
            st.write("**Crimes por dia da semana:**")
            ordem = list(DIAS_SEMANA.keys())
            crimes_dia = df_filtrado["Date"].dt.day_name().value_counts().reindex(ordem, fill_value=0)
            tabela_dias = pd.DataFrame({
                "Dia": [DIAS_SEMANA[d] for d in crimes_dia.index],
                "Crimes": crimes_dia.values,
                "%": (crimes_dia.values / crimes_dia.sum() * 100).round(1),
            })
            st.dataframe(tabela_dias, hide_index=True, width="stretch")

    with tab3:
        st.subheader("Exportar Dados Filtrados")
        st.info("Exporte os dados filtrados para análise externa")
        col1, col2 = st.columns(2)

        with col1:
            limite = 500_000
            if len(df_filtrado) > limite:
                st.warning(
                    f"⚠️ Mais de {limite:,} registros. Para exportar, restrinja os filtros "
                    "(o arquivo ficaria grande demais para o navegador)."
                )
            else:
                csv = df_filtrado.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download como CSV",
                    data=csv,
                    file_name=f"chicago_crimes_filtrados_{datetime.now():%Y%m%d_%H%M}.csv",
                    mime="text/csv",
                    width="stretch",
                )

        with col2:
            st.write("**Resumo do Dataset:**")
            st.write(f"• Registros: {len(df_filtrado):,}")
            st.write(f"• Colunas: {len(df_filtrado.columns)}")
            st.write(f"• Período: {df_filtrado['Date'].min():%d/%m/%Y} a {df_filtrado['Date'].max():%d/%m/%Y}")

    st.markdown("---")
    st.markdown("*Módulo de Análise Estatística de Dados - Chicago Crime Analytics*")


if __name__ == "__main__":
    main()
