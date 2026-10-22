# app.py - Página Inicial do Dashboard
import pandas as pd
import streamlit as st

from data_loader import load_data, ANO_MIN, ANO_MAX

# Configuração da página
st.set_page_config(
    page_title="Crime Analytics Chicago",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Título principal
st.title("🔍 Dashboard para Estudo dos Crimes em Chicago")
st.markdown("### Selecione uma das ferramentas abaixo para explorar os dados de criminalidade")
st.markdown("---")

# Sidebar com seletor de período (afeta apenas o resumo desta página;
# as páginas de análise possuem seus próprios filtros de ano)
st.sidebar.header("📅 Resumo por Período")

# A primeira opção é a que carrega por padrão. Começar pelo período recente, e
# não pelos 11 anos, mantém a página inicial leve: carregar 2014-2024 custa
# ~558 MB de RSS contra ~352 MB de um triênio, e o piso de memória garantido
# pelo Streamlit Community Cloud é de 690 MB.
period_options = {
    "Período Recente (2022-2024)": (2022, 2024),
    f"Dados Completos ({ANO_MIN}-{ANO_MAX})": (ANO_MIN, ANO_MAX),
    "2020-2021": (2020, 2021),
    "2018-2019": (2018, 2019),
    "2016-2017": (2016, 2017),
    "2014-2015": (2014, 2015),
}

selected_period_label = st.sidebar.selectbox(
    "Selecione o período para o resumo:",
    list(period_options.keys()),
)
selected_period = period_options[selected_period_label]

# Carrega só os arquivos do período escolhido (resultado fica em cache)
df = load_data(selected_period)

# Cards de navegação
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📊 Análise Estatística")
    st.markdown("Navegue, filtre e explore o banco de dados completo de crimes")
    if st.button("Acessar Análise Estatística", key="btn1", width="stretch"):
        st.switch_page("pages/01_analise_estatistica.py")

with col2:
    st.markdown("### 📈 Análise Exploratória")
    st.markdown("Visualizações avançadas, tendências e métricas detalhadas")
    if st.button("Acessar Análise Exploratória", key="btn2", width="stretch"):
        st.switch_page("pages/02_analise_exploratoria.py")

with col3:
    st.markdown("### 🔮 Predição de Dados")
    st.markdown("Modelos de machine learning e previsões futuras")
    if st.button("Acessar Predição de Dados", key="btn3", width="stretch"):
        st.switch_page("pages/03_predicao_crimes.py")

with col4:
    st.markdown("### 🗺️ Análise Geográfica")
    st.markdown("Mapas interativos, hotspots e análise por região")
    if st.button("Acessar Análise Geográfica", key="btn4", width="stretch"):
        st.switch_page("pages/04_analise_espacial.py")

# Informações dos dados carregados
st.markdown("---")
st.markdown(f"### 📋 Informações dos Dados — {selected_period_label}")

if df.empty:
    st.error("❌ Nenhum dado encontrado. Verifique se os arquivos estão na pasta 'data/processed'.")
else:
    col_info1, col_info2, col_info3, col_info4 = st.columns(4)

    with col_info1:
        st.metric("Total de Registros", f"{len(df):,}")

    with col_info2:
        min_date, max_date = df["Date"].min(), df["Date"].max()
        if pd.notna(min_date) and pd.notna(max_date):
            st.metric("Período", f"{min_date:%Y} a {max_date:%Y}")
        else:
            st.metric("Período", "Datas inválidas")

    with col_info3:
        st.metric("Tipos de Crime", df["Primary Type"].nunique())

    with col_info4:
        st.metric("Distritos", df["District"].nunique() if "District" in df.columns else "N/A")

    with st.sidebar.expander("ℹ️ Detalhes dos Dados Carregados", expanded=True):
        st.write(f"📈 **Total de registros**: {len(df):,}")
        if pd.notna(min_date) and pd.notna(max_date):
            st.write(f"📅 **Período**: {min_date:%d/%m/%Y} a {max_date:%d/%m/%Y}")
        top_crimes = df["Primary Type"].value_counts().head(3)
        st.write("🔍 **Top 3 crimes**:")
        for crime, count in top_crimes.items():
            st.write(f"   - {crime}: {count:,}")
        if "Arrest" in df.columns:
            st.write(f"🚔 **Taxa de prisões**: {df['Arrest'].mean() * 100:.1f}%")

# Informações adicionais
st.markdown("---")
st.markdown(f"""
### 📋 Sobre o Sistema
Este sistema de análise permite explorar dados históricos de criminalidade de Chicago através de diferentes perspectivas.

**Fonte dos dados**: Chicago Police Department ({ANO_MIN}-{ANO_MAX})

**Desenvolvido por**: Matheus Henrique Massuda

**Estratégia de dados**: Divisão em arquivos de 2 anos; apenas os arquivos do período
selecionado são lidos do disco e o resultado fica em cache.
""")
