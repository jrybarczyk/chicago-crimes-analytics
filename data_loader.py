# data_loader.py - Carregamento centralizado dos dados de crimes de Chicago
#
# Este módulo NÃO desenha nada na tela. Ele lê os arquivos Parquet ou CSV da pasta
# data/processed/ e devolve um DataFrame. Assim ele pode ser importado por
# qualquer página sem efeitos colaterais.
#
# Memória (medido com a pilha da aplicação importada, em processos limpos):
#   2014-2024, 21 colunas ................ 967 MB de RSS
#   2014-2024, só as colunas usadas ...... 558 MB
#   período selecionado, colunas usadas .. 352 MB
# O piso de memória garantido pelo Streamlit Community Cloud é de 690 MB, então
# carregar tudo não cabe. Por isso o padrão aqui é ler apenas os arquivos do
# período pedido e apenas as colunas que a aplicação de fato usa.
import os
import re
import glob

import pandas as pd
import streamlit as st

# Pasta data/processed relativa a este arquivo, para funcionar independente do
# diretório de onde o `streamlit run` foi chamado. Pode ser sobrescrita pela
# variável de ambiente CHICAGO_DATA_DIR (útil em testes e em deploys que montam
# os dados em outro caminho).
# Formatos aceitos: .parquet (preferido: ~5x menor e muito mais rápido) e .csv.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CHICAGO_DATA_DIR") or os.path.join(BASE_DIR, "data", "processed")

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

# Colunas efetivamente referenciadas por app.py e pelas quatro páginas.
# As demais (ID, IUCR, Description, Beat, Ward, Community Area, FBI Code,
# X Coordinate, Y Coordinate, Day, DayOfWeek) somam 118 MB dos 215 MB do
# DataFrame completo e não são lidas por nenhum gráfico ou métrica. Para exibir
# a linha bruta inteira, chame load_data(..., colunas="todas").
COLUNAS_APP = [
    "Date", "Primary Type", "Arrest", "Domestic", "District",
    "Year", "Latitude", "Longitude", "Month", "Hour",
]

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


def _resolver_colunas(colunas):
    """None/'app' -> COLUNAS_APP; 'todas' -> None (lê tudo); lista -> a lista."""
    if colunas in (None, "app"):
        return list(COLUNAS_APP)
    if colunas == "todas":
        return None
    return list(colunas)


def _ler_parquet(caminho, colunas=None):
    """Lê um Parquet gerado por `converter_para_parquet` (tipos já otimizados)."""
    if colunas is not None:
        # Só as colunas pedidas saem do disco: o pyarrow não materializa as
        # demais. A interseção com o schema tolera arquivos antigos aos quais
        # falte alguma coluna derivada.
        import pyarrow.parquet as pq
        disponiveis = set(pq.ParquetFile(caminho).schema_arrow.names)
        colunas = [c for c in colunas if c in disponiveis]
    parte = pd.read_parquet(caminho, columns=colunas)
    for col in COLUNAS_CATEGORICAS:
        if col in parte.columns:
            parte[col] = parte[col].astype("category")
    return parte


def _ler_csv(caminho, colunas=None):
    """Lê um CSV com tipos otimizados e converte a coluna de data."""
    cabecalho = pd.read_csv(caminho, nrows=0).columns
    usecols = [c for c in cabecalho if c not in COLUNAS_IGNORADAS]
    if colunas is not None:
        # A coluna de data é indispensável mesmo quando não foi pedida.
        necessarias = set(colunas) | {"Date", "Data"}
        usecols = [c for c in usecols if c in necessarias]
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


def _ler_arquivo(caminho, colunas=None):
    if caminho.endswith(".parquet"):
        return _ler_parquet(caminho, colunas)
    return _ler_csv(caminho, colunas)


def converter_para_parquet(pasta=DATA_DIR):
    """Converte todos os CSVs da pasta em .parquet (zstd). Uso: python data_loader.py"""
    for csv in sorted(glob.glob(os.path.join(pasta, "chicago_crimes_*.csv"))):
        destino = csv[:-4] + ".parquet"
        _ler_csv(csv).to_parquet(destino, compression="zstd", index=False)
        print(f"{os.path.basename(destino)}: {os.path.getsize(destino) / 1e6:.1f} MB")


def _carregar(years_range, colunas):
    """Leitura efetiva, sem cache. Separada para poder ser testada."""
    if not os.path.isdir(DATA_DIR):
        return pd.DataFrame()

    arquivos = listar_arquivos(years_range)
    if not arquivos:
        return pd.DataFrame()

    cols = _resolver_colunas(colunas)
    partes = []
    for arq in arquivos:
        try:
            parte = _ler_arquivo(arq, cols)
            # Filtrar cada parte ANTES do concat reduz o pico de memória: sem
            # isso as partes e o resultado concatenado coexistem em tamanho cheio.
            if years_range is not None and "Year" in parte.columns:
                inicio, fim = years_range
                parte = parte[(parte["Year"] >= inicio) & (parte["Year"] <= fim)]
            parte = parte.dropna(subset=["Date"])
            partes.append(parte)
        except Exception as e:  # arquivo corrompido não derruba os demais
            st.warning(f"⚠️ Arquivo ignorado ({os.path.basename(arq)}): {e}")

    if not partes:
        return pd.DataFrame()

    df = pd.concat(partes, ignore_index=True)
    partes.clear()  # libera as partes antes de qualquer outra alocação

    # Após o concat as categorias de cada parte são unidas; reconverter garante
    # que as colunas continuem categóricas (e leves).
    for col in COLUNAS_CATEGORICAS:
        if col in df.columns:
            df[col] = df[col].astype("category")

    return df.reset_index(drop=True)


# cache_resource e não cache_data: cache_data guarda uma cópia serializada e
# devolve uma cópia nova a cada chamada, duplicando o maior objeto da aplicação.
# O DataFrame devolvido aqui é tratado como SOMENTE LEITURA pelas páginas —
# filtros criam views ou cópias derivadas, nunca alteram este objeto.
@st.cache_resource(show_spinner="Carregando dados de crimes...")
def load_data(years_range=None, colunas="app"):
    """Carrega os crimes de Chicago da pasta data/processed.

    years_range: tupla (ano_inicial, ano_final) ou None para todos os dados.
        Só os arquivos que cobrem o intervalo pedido são lidos do disco.
    colunas: "app" (padrão, só as colunas usadas pela aplicação), "todas",
        ou uma lista explícita de nomes.
    Retorna um DataFrame vazio se nada puder ser carregado.

    ATENÇÃO: o objeto devolvido é compartilhado entre as páginas. Não modifique
    o DataFrame no lugar; use .copy() antes de qualquer atribuição.
    """
    if isinstance(colunas, list):
        colunas = tuple(colunas)  # cache_resource exige argumentos hasheáveis
    return _carregar(years_range, list(colunas) if isinstance(colunas, tuple) else colunas)


def load_all(colunas="app"):
    """Atalho para o dataset completo (2014-2024).

    Evite em páginas interativas: carregar os 11 anos de uma vez consome ~558 MB
    de RSS mesmo só com as colunas da aplicação. Prefira
    load_data((ano_inicial, ano_final)) com o período que o usuário selecionou.
    """
    return load_data((ANO_MIN, ANO_MAX), colunas)


if __name__ == "__main__":
    converter_para_parquet()
