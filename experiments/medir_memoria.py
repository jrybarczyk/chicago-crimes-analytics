#!/usr/bin/env python
"""experiments/medir_memoria.py - Mede o RSS do processo por estratégia de carga.

O Streamlit Community Cloud garante 690 MB de memória por aplicação. Este script
reproduz os números da seção "Memória" do README, cada cenário em um processo
limpo (medir vários no mesmo processo infla os resultados: o alocador não
devolve a memória ao sistema entre eles).

Uso:
    python experiments/medir_memoria.py            # roda todos os cenários
    python experiments/medir_memoria.py tudo_todas # um cenário só (uso interno)
"""
import os
import subprocess
import sys

CENARIOS = {
    "tudo_todas": ("load_all(colunas='todas') - comportamento anterior", None),
    "tudo_app": ("load_all() - 11 anos, colunas da aplicacao", None),
    "trienio_app": ("load_data((2022,2024)) - o que as paginas fazem", None),
    "predicao": ("caminho completo de predicao (Prophet + RF ajustados)", None),
}


def medir(cenario):
    import gc
    import psutil
    proc = psutil.Process()
    pico = [0.0]

    def rss():
        v = proc.memory_info().rss / 1e6
        pico[0] = max(pico[0], v)
        return v

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import pandas  # noqa: F401
    import streamlit  # noqa: F401
    import plotly.express  # noqa: F401
    import folium  # noqa: F401
    from sklearn.ensemble import RandomForestRegressor  # noqa: F401
    from prophet import Prophet  # noqa: F401
    base = rss()

    from data_loader import load_all, load_data
    import forecasting as fc

    if cenario == "tudo_todas":
        df = load_all(colunas="todas")
    elif cenario == "tudo_app":
        df = load_all()
    elif cenario == "trienio_app":
        df = load_data((2022, 2024))
    elif cenario == "predicao":
        df = load_data((2014, 2018), colunas=["Date", "Primary Type", "Year"])
        sub = df[(df["Primary Type"] == "THEFT") & df["Year"].between(2014, 2018)]
        s = fc.serie_diaria(sub)
        treino, teste = s[s.index.year <= 2017], s[s.index.year == 2018]
        fc.rodar_prophet(treino, teste)
        fc.rodar_random_forest(treino, teste, 200, 14, modo_recursivo=True, n_jobs=1)
    else:
        raise SystemExit(f"cenário desconhecido: {cenario}")

    gc.collect()
    rss()
    print(f"{cenario:14s} linhas={len(df):>9,} colunas={df.shape[1]:>2}  "
          f"imports={base:6.0f} MB  pico={pico[0]:6.0f} MB  dados=+{pico[0] - base:5.0f} MB")


def main():
    if len(sys.argv) > 1:
        medir(sys.argv[1])
        return
    print("Piso de memória garantido pelo Streamlit Community Cloud: 690 MB\n")
    for cenario, (descricao, _) in CENARIOS.items():
        print(f"# {descricao}")
        subprocess.run([sys.executable, os.path.abspath(__file__), cenario], check=False)
        print()


if __name__ == "__main__":
    main()
