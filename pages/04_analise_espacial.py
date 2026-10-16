# pages/04_analise_espacial.py - Mapas, hotspots e clusters espaciais
import sys
import os
import warnings

import numpy as np
import pandas as pd
import folium
from folium.plugins import HeatMap, FastMarkerCluster
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium
from sklearn.cluster import DBSCAN

# Configuração da página DEVE SER SEMPRE A PRIMEIRA COISA
st.set_page_config(page_title="Análise Espacial - Crimes Chicago", page_icon="🗺️", layout="wide")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_all  # noqa: E402

warnings.filterwarnings("ignore")

RAIO_TERRA_M = 6_371_000
CHICAGO_CENTER = [41.8781, -87.6298]
CHICAGO_BOUNDS = {"lat_min": 41.6, "lat_max": 42.1, "lng_min": -88.0, "lng_max": -87.5}
CRIME_COLORS = {
    "THEFT": "blue", "BATTERY": "red", "ASSAULT": "orange", "BURGLARY": "green",
    "ROBBERY": "purple", "NARCOTICS": "darkred", "CRIMINAL DAMAGE": "gray",
    "MOTOR VEHICLE THEFT": "cadetblue", "DECEPTIVE PRACTICE": "pink",
}


def rodar_dbscan(coords_graus, eps_metros, min_samples):
    """DBSCAN com distância geodésica real (haversine) e eps em metros.

    A normalização z-score usada antes distorcia as distâncias: um grau de
    latitude e um de longitude não têm o mesmo comprimento em Chicago.
    """
    coords_rad = np.radians(coords_graus)
    db = DBSCAN(eps=eps_metros / RAIO_TERRA_M, min_samples=min_samples,
                metric="haversine", algorithm="ball_tree", n_jobs=-1)
    return db.fit_predict(coords_rad)


def main():
    st.title("🗺️ Análise Espacial de Crimes")
    st.markdown("Explore a distribuição geográfica dos crimes, identifique hotspots e padrões espaciais.")

    if st.button("← Voltar para Página Inicial"):
        st.switch_page("app.py")

    df = load_all()
    if df.empty:
        st.error("❌ Não foi possível carregar os dados. Verifique se os arquivos estão na pasta 'data/processed'.")
        return

    # ---------------- Filtros ----------------
    st.sidebar.header("🎯 Controles de Análise")
    st.sidebar.subheader("🔍 Filtros de Dados")

    crime_types = sorted(df["Primary Type"].unique())
    padrao = [c for c in ("THEFT", "BATTERY", "ASSAULT") if c in crime_types] or crime_types[:3]
    selected_crimes = st.sidebar.multiselect("Tipos de Crime:", options=crime_types, default=padrao)

    available_years = sorted(int(a) for a in df["Year"].unique())
    selected_years = st.sidebar.multiselect("Anos:", options=available_years, default=available_years[-1:])

    start_month, end_month = st.sidebar.slider("Meses (Jan=1, Dez=12):", 1, 12, (1, 12))

    st.sidebar.subheader("⚙️ Visualização do Mapa")
    analysis_type = st.sidebar.radio(
        "Tipo de Visualização:", ["Mapa de Calor", "Clusters DBSCAN", "Pontos Individuais"]
    )
    max_pontos = st.sidebar.select_slider(
        "Máximo de pontos no mapa:", options=[2_000, 5_000, 10_000, 20_000, 50_000], value=10_000,
        help="Amostra aleatória para manter o navegador responsivo.",
    )

    # Parâmetros do DBSCAN sempre definidos: a aba de clusters também os usa
    # (antes isso gerava NameError quando outra visualização estava selecionada).
    st.sidebar.subheader("🔬 Parâmetros DBSCAN")
    eps_metros = st.sidebar.slider("Raio de vizinhança (metros):", 50, 1000, 200, step=25)
    min_samples_value = st.sidebar.slider("Mínimo de pontos por cluster:", 5, 200, 30)
    amostra_dbscan = st.sidebar.select_slider(
        "Pontos usados no DBSCAN:", options=[10_000, 25_000, 50_000, 100_000], value=50_000
    )

    if not selected_crimes or not selected_years:
        st.warning("⚠️ Selecione pelo menos um tipo de crime e um ano.")
        return

    mask = (
        df["Primary Type"].isin(selected_crimes)
        & df["Year"].isin(selected_years)
        & df["Month"].between(start_month, end_month)
        & df["Latitude"].between(CHICAGO_BOUNDS["lat_min"], CHICAGO_BOUNDS["lat_max"])
        & df["Longitude"].between(CHICAGO_BOUNDS["lng_min"], CHICAGO_BOUNDS["lng_max"])
    )
    df_filtered = df[mask]

    st.sidebar.info(f"📊 **Dados filtrados:** {len(df_filtered):,} registros")

    if df_filtered.empty:
        st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados (após remover coordenadas inválidas).")
        return

    if len(df_filtered) > max_pontos:
        display_df = df_filtered.sample(n=max_pontos, random_state=42)
        aviso_amostra = f"📊 Mostrando amostra de {max_pontos:,} de {len(df_filtered):,} registros."
    else:
        display_df = df_filtered
        aviso_amostra = None

    tab1, tab2, tab3 = st.tabs(["🗺️ Mapa Interativo", "📈 Análise por Distrito", "🔍 Análise de Clusters"])

    # ================= Mapa =================
    with tab1:
        st.subheader("Mapa Interativo de Crimes")
        if aviso_amostra:
            st.info(aviso_amostra)

        m = folium.Map(location=CHICAGO_CENTER, zoom_start=11, tiles="CartoDB positron")
        lat = display_df["Latitude"].to_numpy()
        lng = display_df["Longitude"].to_numpy()

        if analysis_type == "Mapa de Calor":
            HeatMap(np.column_stack([lat, lng]).tolist(), radius=10, blur=15, max_zoom=13).add_to(m)

        elif analysis_type == "Clusters DBSCAN":
            with st.spinner("Executando DBSCAN..."):
                labels = rodar_dbscan(np.column_stack([lat, lng]), eps_metros, min_samples_value)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            paleta = px.colors.qualitative.Dark24
            for la, lo, c in zip(lat, lng, labels):
                if c == -1:
                    continue
                folium.CircleMarker(
                    location=[la, lo], radius=3, color=paleta[c % len(paleta)],
                    fill=True, fill_opacity=0.7, popup=f"Cluster {c}",
                ).add_to(m)
            st.success(f"✅ {n_clusters} clusters identificados (ruído: {(labels == -1).mean() * 100:.1f}% dos pontos)")

        else:  # Pontos individuais
            # FastMarkerCluster desenha dezenas de milhares de pontos sem travar
            popups = [
                f"<b>Tipo:</b> {r['Primary Type']}<br><b>Data:</b> {r['Date']:%d/%m/%Y %H:%M}"
                f"<br><b>Distrito:</b> {int(r['District']) if pd.notna(r['District']) else 'N/A'}"
                f"<br><b>Prisão:</b> {'Sim' if r['Arrest'] else 'Não'}"
                for _, r in display_df[["Primary Type", "Date", "District", "Arrest"]].iterrows()
            ]
            callback = """
            function (row) {
                var marker = L.circleMarker(new L.LatLng(row[0], row[1]), {radius: 4, color: row[3], fillOpacity: 0.7});
                marker.bindPopup(row[2]);
                return marker;
            };
            """
            cores = [CRIME_COLORS.get(t, "black") for t in display_df["Primary Type"]]
            dados = [[a, b, p, c] for a, b, p, c in zip(lat, lng, popups, cores)]
            FastMarkerCluster(dados, callback=callback).add_to(m)
            legenda = ", ".join(f"{t}: {CRIME_COLORS.get(t, 'black')}" for t in selected_crimes)
            st.caption(f"Cores: {legenda}")

        st_folium(m, width=None, height=600, returned_objects=[])

        col1, col2, col3 = st.columns(3)
        col1.metric("Crimes no Mapa", f"{len(display_df):,}")
        col2.metric("Tipos de Crime", display_df["Primary Type"].nunique())
        col3.metric("Distritos", display_df["District"].nunique())

    # ================= Distritos =================
    with tab2:
        st.subheader("Análise por Distrito")
        if "District" not in df_filtered.columns:
            st.warning("⚠️ Coluna 'District' não encontrada nos dados.")
        else:
            por_distrito = df_filtered["District"].value_counts().sort_values(ascending=False)
            por_distrito = por_distrito[por_distrito > 0]
            por_distrito.index = por_distrito.index.astype(int)
            total = int(por_distrito.sum())

            col1, col2 = st.columns(2)
            col1.metric("Total de Crimes", f"{total:,}")
            col1.metric("Distritos com Ocorrências", len(por_distrito))
            col2.metric("Anos Analisados", ", ".join(map(str, selected_years)))
            col2.metric("Meses", f"{start_month} a {end_month}")

            tabela = pd.DataFrame({
                "Distrito": por_distrito.index,
                "Nº de Crimes": por_distrito.values,
                "Proporção (%)": (por_distrito.values / total * 100).round(2),
            })
            if "Arrest" in df_filtered.columns:
                taxa = df_filtered.groupby("District")["Arrest"].mean() * 100
                tabela["Taxa de prisão (%)"] = tabela["Distrito"].map(lambda d: round(taxa.get(float(d), np.nan), 1))

            st.subheader("📋 Estatísticas por Distrito")
            st.dataframe(tabela, hide_index=True, width="stretch")

            st.subheader("📊 Distribuição por Distrito")
            fig = px.bar(tabela, x=tabela["Distrito"].astype(str), y="Nº de Crimes",
                         title="Crimes por Distrito", labels={"x": "Distrito"})
            st.plotly_chart(fig, width="stretch")

            # Mapa de calor hora × distrito: onde E quando
            st.subheader("🕒 Hora do dia × Distrito")
            pivot = pd.crosstab(df_filtered["District"].astype(int), df_filtered["Hour"])
            fig_h = px.imshow(pivot, aspect="auto", color_continuous_scale="Reds",
                              labels=dict(x="Hora", y="Distrito", color="Crimes"))
            st.plotly_chart(fig_h, width="stretch")

    # ================= Clusters =================
    with tab3:
        st.subheader("Análise de Clusters com DBSCAN")
        st.caption(f"Parâmetros atuais: raio {eps_metros} m, mínimo {min_samples_value} pontos, "
                   f"até {amostra_dbscan:,} pontos (ajuste na barra lateral).")

        if st.button("🔍 Executar Análise de Clusters", type="primary"):
            with st.spinner("Processando clusters..."):
                try:
                    coords = df_filtered[["Latitude", "Longitude"]].to_numpy()
                    if len(coords) > amostra_dbscan:
                        rng = np.random.default_rng(42)
                        coords = coords[rng.choice(len(coords), amostra_dbscan, replace=False)]
                        st.info(f"📊 Usando amostra de {amostra_dbscan:,} pontos de {len(df_filtered):,} totais")

                    labels = rodar_dbscan(coords, eps_metros, min_samples_value)

                    unicos = set(labels)
                    n_clusters = len(unicos) - (1 if -1 in unicos else 0)
                    n_noise = int((labels == -1).sum())

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Clusters Identificados", n_clusters)
                    c2.metric("Pontos de Ruído", f"{n_noise:,}")
                    c3.metric("Taxa de Ruído", f"{n_noise / len(labels) * 100:.1f}%")
                    c4.metric("Pontos Analisados", f"{len(coords):,}")

                    cluster_df = pd.DataFrame({"Latitude": coords[:, 0], "Longitude": coords[:, 1], "Cluster": labels})

                    st.subheader("📈 Visualização dos Clusters")
                    plot_df = cluster_df.copy()
                    plot_df["Cluster"] = plot_df["Cluster"].map(lambda c: "Ruído" if c == -1 else f"C{c}")
                    fig = px.scatter(
                        plot_df, x="Longitude", y="Latitude", color="Cluster", opacity=0.6,
                        title=f"{n_clusters} clusters, {n_noise:,} pontos de ruído",
                        height=650, color_discrete_map={"Ruído": "lightgray"},
                    )
                    fig.update_traces(marker=dict(size=4))
                    fig.update_yaxes(scaleanchor="x", scaleratio=1.34)  # proporção aprox. lat/lon em Chicago
                    st.plotly_chart(fig, width="stretch")

                    if n_clusters > 0:
                        st.subheader("🔍 Hotspots (clusters ordenados por tamanho)")
                        stats = (
                            cluster_df[cluster_df["Cluster"] != -1]
                            .groupby("Cluster")
                            .agg(N_Pontos=("Latitude", "size"), Latitude_Media=("Latitude", "mean"),
                                 Longitude_Media=("Longitude", "mean"))
                            .sort_values("N_Pontos", ascending=False)
                            .round(5)
                        )
                        stats["% dos pontos"] = (stats["N_Pontos"] / len(coords) * 100).round(2)
                        st.dataframe(stats.head(20), width="stretch")
                    else:
                        st.info("Nenhum cluster encontrado. Aumente o raio ou reduza o mínimo de pontos.")

                except Exception as e:
                    st.error(f"❌ Erro na análise de clusters: {e}")

    st.markdown("---")
    st.markdown("""
    **💡 Dicas de Uso:**
    - **Mapa de Calor**: identifica hotspots de criminalidade
    - **Clusters DBSCAN**: agrupa ocorrências próximas (raio em metros) e marca o resto como ruído
    - **Pontos Individuais**: agrupa no zoom e mostra detalhes de cada crime ao clicar
    - **Análise por Distrito**: compara distribuição e taxa de prisão entre regiões administrativas
    """)
    st.markdown("**Módulo de Análise Espacial - Chicago Crime Analytics**")


if __name__ == "__main__":
    main()
