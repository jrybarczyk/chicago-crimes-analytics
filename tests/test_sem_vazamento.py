# tests/test_sem_vazamento.py
"""Testes que impedem a reintrodução do vazamento temporal corrigido na v1.0.0.

Rodar com:  pytest tests/ -v
Depende apenas de numpy, pandas e pytest.
"""
import sys, os
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# As funções de previsão precisam estar importáveis sem Streamlit.
# Enquanto viverem em pages/03_predicao_crimes.py, este import falha — e é
# exatamente por isso que a extração para forecasting.py é recomendada.
from forecasting import features_lags, features_calendario, serie_diaria, rodar_random_forest


def serie_sintetica(n=400, semente=0):
    rng = np.random.default_rng(semente)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    base = 40 + 8 * np.sin(2 * np.pi * np.arange(n) / 7)
    return pd.Series(np.maximum(0, base + rng.normal(0, 5, n)).round(),
                     index=idx, name="y").rename_axis("ds")


# ---------------------------------------------------------------- causalidade
def test_atributos_nao_dependem_do_futuro():
    """Nenhum atributo na posição i pode mudar quando y[i:] é perturbado.

    Este é o teste que falha na versão original do código: as médias móveis
    calculadas sobre janelas contendo o dia-alvo tornam o alvo recuperável.
    """
    y = serie_sintetica()
    i = len(y) // 2
    y_perturbada = y.copy()
    y_perturbada.iloc[i:] += 1000                      # altera apenas o futuro

    a = features_lags(y, 14)
    b = features_lags(y_perturbada, 14)
    dif = (a.iloc[:i + 1] - b.iloc[:i + 1]).abs().max()
    contaminadas = sorted(dif[dif > 1e-9].index)

    assert not contaminadas, f"atributos dependem do futuro: {contaminadas}"


def test_lag_k_reproduz_o_valor_deslocado():
    y = serie_sintetica()
    f = features_lags(y, 14)
    for k in (1, 7, 14):
        esperado = y.shift(k)
        pd.testing.assert_series_equal(f[f"lag_{k}d"], esperado, check_names=False)


def test_media_movel_exclui_o_dia_alvo():
    y = serie_sintetica()
    f = features_lags(y, 14)
    i = 100
    janela = y.iloc[i - 7:i]                           # 7 dias ANTERIORES a i
    assert f["rolling_mean_7d"].iloc[i] == pytest.approx(janela.mean())


# ------------------------------------------------------------------- previsão
def test_modo_recursivo_nao_le_o_teste():
    """A previsão recursiva deve ser idêntica se os valores reais do período
    de teste forem substituídos por lixo: o modelo não pode consultá-los."""
    y = serie_sintetica(730)
    treino, teste = y.iloc[:550], y.iloc[550:]
    teste_adulterado = pd.Series(np.full(len(teste), 9999.0), index=teste.index, name="y")

    # n_jobs=1: teste não deve depender de paralelismo (determinismo e CI).
    p1, _ = rodar_random_forest(treino, teste, 50, 14, modo_recursivo=True, n_jobs=1)
    p2, _ = rodar_random_forest(treino, teste_adulterado, 50, 14, modo_recursivo=True, n_jobs=1)
    pd.testing.assert_series_equal(p1, p2, check_names=False)


def test_modo_recursivo_executa():
    """Regressão: `valores = hist.values` devolvia array somente-leitura sob
    copy-on-write do pandas >= 2.0 e levantava ValueError na atribuição."""
    y = serie_sintetica(730)
    previsao, _ = rodar_random_forest(y.iloc[:550], y.iloc[550:], 50, 14,
                                      modo_recursivo=True, n_jobs=1)
    assert len(previsao) == 180
    assert previsao.notna().all() and (previsao >= 0).all()


# ----------------------------------------------------------------- série diária
def test_dias_sem_ocorrencia_viram_zero():
    registros = pd.DataFrame({"Date": pd.to_datetime(
        ["2021-01-01 10:00", "2021-01-01 22:00", "2021-01-05 03:00"])})
    s = serie_diaria(registros)
    assert len(s) == 5                                  # 01 a 05 de janeiro
    assert s.loc["2021-01-01"] == 2
    assert (s.loc["2021-01-02":"2021-01-04"] == 0).all()


def test_indicador_de_feriado():
    idx = pd.date_range("2018-07-01", "2018-07-07", freq="D")
    f = features_calendario(idx, [2018])
    assert f.loc["2018-07-04", "is_holiday"] == 1       # Independence Day
    assert f.loc["2018-07-03", "is_holiday"] == 0
