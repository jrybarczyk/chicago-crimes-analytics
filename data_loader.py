# data_loader.py - Carregamento centralizado dos dados de crimes de Chicago
#
# Este módulo NÃO desenha nada na tela. Ele lê os arquivos Parquet ou CSV da pasta
# data/processed/ e devolve um DataFrame. Assim ele pode ser importado por
# qualquer página sem efeitos colaterais (antes, importar app.py renderizava
# a página inicial inteira dentro das subpáginas).
import os
import re
import glob

import pandas as pd
import streamlit as st

# Pasta data/processed relativa a este arquivo, para funcionar independente do
# diretório de onde o `streamlit run` foi chamado.
# Formatos aceitos: .parquet (preferido: ~5x menor e muito mais rápido) e .csv.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

ANO_MIN, ANO_MAX = 2014, 2024

# Tipos de dados enxutos: reduz bastante a memória (2,7 milhões de linhas).
DTYPES = {
    "ID": "int64",
    "IUCR": "category",
    "Primary Type": "category",
    "Description": "category",
    "Arrest": "bool",
    "Domestic": "bool",
    "Beat": "int32",
    "District": "float32",
    "Ward": "float32",
    "Community Area": "float32",
    "FBI Code": "category",
    "X Coordinate": "float64",
    "Y Coordinate": "float64",
    "Year": "int16",
    "Latitude": "float64",
    "Longitude": "float64",
    "Month": "int8",
    "Day": "int8",
    "Hour": "int8",
    "DayOfWeek": "int8",
}

# A coluna Location é redundante (é só "(lat, lon)" em texto) e pesa muito.
COLUNAS_IGNORADAS = {"Location"}

_PADRAO_ARQUIVO = re.compile(r"chicago_crimes_(\d{4})_(\d{4})\.(parquet|csv)$")
COLUNAS_CATEGORICAS = ("Primary Type", "Description", "IUCR", "FBI Code")


def listar_arquivos(years_range=None):
    """Lista os arquivos cujo intervalo de anos intersecta `years_range`.

    years_range: tupla (ano_inicial, ano_final) ou None para todos.
    """
    parquets = glob.glob(os.path.join(DATA_DIR, "chicago_crimes_*.parquet"))
    csvs = glob.glob(os.path.join(DATA_DIR, "chicago_crimes_*.csv"))
    # Se um período existe nos dois formatos, usa só o parquet
    periodos_parquet = {os.path.splitext(os.path.basename(p))[0] for p in parquets}
    csvs = [c for c in csvs if os.path.splitext(os.path.basename(c))[0] not in periodos_parquet]
    arquivos = sorted(parquets + csvs)
    if years_range is None:
        return arquivos

    inicio, fim = years_range
    selecionados = []
    for arq in arquivos:
        m = _PADRAO_ARQUIVO.search(os.path.basename(arq))
        if not m:
            # Nome fora do padrão: carrega e deixa o filtro por ano decidir
            selecionados.append(arq)
            continue
        a_ini, a_fim = int(m.group(1)), int(m.group(2))
        if a_fim >= inicio and a_ini <= fim:
            selecionados.append(arq)
    return selecionados


def _ler_parquet(caminho):
    """Lê um Parquet gerado por `converter_para_parquet` (tipos já otimizados)."""
    parte = pd.read_parquet(caminho)
    for col in COLUNAS_CATEGORICAS:
        if col in parte.columns:
            parte[col] = parte[col].astype("category")
    return parte


def _ler_arquivo(caminho):
    if caminho.endswith(".parquet"):
        return _ler_parquet(caminho)
    return _ler_csv(caminho)


def converter_para_parquet(pasta=DATA_DIR):
    """Converte todos os CSVs da pasta em .parquet (zstd). Uso: python data_loader.py"""
    for csv in sorted(glob.glob(os.path.join(pasta, "chicago_crimes_*.csv"))):
        destino = csv[:-4] + ".parquet"
        _ler_csv(csv).to_parquet(destino, compression="zstd", index=False)
        print(f"{os.path.basename(destino)}: {os.path.getsize(destino) / 1e6:.1f} MB")


def _ler_csv(caminho):
    """Lê um CSV com tipos otimizados e converte a coluna de data."""
    cabecalho = pd.read_csv(caminho, nrows=0).columns
    usecols = [c for c in cabecalho if c not in COLUNAS_IGNORADAS]
    dtypes = {c: t for c, t in DTYPES.items() if c in usecols}

    parte = pd.read_csv(caminho, usecols=usecols, dtype=dtypes)

    coluna_data = "Date" if "Date" in parte.columns else ("Data" if "Data" in parte.columns else None)
    if coluna_data is None:
        raise ValueError(f"Nenhuma coluna de data encontrada em {os.path.basename(caminho)}")

    # Formato fixo é muito mais rápido do que a inferência automática
    parte["Date"] = pd.to_datetime(parte[coluna_data], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    if coluna_data != "Date":
        parte = parte.drop(columns=[coluna_data])

    # Garante colunas derivadas usadas pelas páginas
    if "Year" not in parte.columns:
        parte["Year"] = parte["Date"].dt.year.astype("int16")
    if "Month" not in parte.columns:
        parte["Month"] = parte["Date"].dt.month.astype("int8")
    if "Hour" not in parte.columns:
        parte["Hour"] = parte["Date"].dt.hour.astype("int8")

    return parte


@st.cache_data(show_spinner="Carregando dados de crimes...")
def load_data(years_range=None):
    """Carrega os crimes de Chicago da pasta data/processed.

    years_range: tupla (ano_inicial, ano_final) ou None para todos os dados.
    Só os arquivos que cobrem o intervalo pedido são lidos do disco.
    Retorna um DataFrame vazio se nada puder ser carregado.
    """
    if not os.path.isdir(DATA_DIR):
        return pd.DataFrame()

    arquivos = listar_arquivos(years_range)
    if not arquivos:
        return pd.DataFrame()

    partes = []
    for arq in arquivos:
        try:
            partes.append(_ler_arquivo(arq))
        except Exception as e:  # arquivo corrompido não derruba os demais
            st.warning(f"⚠️ Arquivo ignorado ({os.path.basename(arq)}): {e}")

    if not partes:
        return pd.DataFrame()

    df = pd.concat(partes, ignore_index=True)

    # Após o concat as categorias de cada parte são unidas; reconverter garante
    # que as colunas continuem categóricas (e leves).
    for col in COLUNAS_CATEGORICAS:
        if col in df.columns:
            df[col] = df[col].astype("category")

    df = df.dropna(subset=["Date"])

    if years_range is not None:
        inicio, fim = years_range
        df = df[(df["Year"] >= inicio) & (df["Year"] <= fim)]

    return df.reset_index(drop=True)


def load_all():
    """Atalho para o dataset completo (2014-2024)."""
    return load_data((ANO_MIN, ANO_MAX))


if __name__ == "__main__":
    converter_para_parquet()
