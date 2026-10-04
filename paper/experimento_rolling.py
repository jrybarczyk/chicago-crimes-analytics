# Experimento ampliado: avaliação com origem deslizante (rolling origin).
# Para cada série (tipo de crime) e cada ano de teste T em 2018..2024, treina com
# os 4 anos anteriores (T-4..T-1) e prevê os 365 dias de T sem acesso aos valores reais.
# Modelos: Prophet, Random Forest recursivo, RF 1 passo (referência), baselines ingênuas.
# Saída: paper/resultados/metricas.csv e paper/resultados/previsoes.pkl
import os, sys, time, pickle, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, "..", "Codigo_VS_code")
sys.path.insert(0, RAIZ)
import importlib.util
import data_loader as dl
spec = importlib.util.spec_from_file_location("pred", os.path.join(RAIZ, "pages", "03_predicao_crimes.py"))
pred = importlib.util.module_from_spec(spec); spec.loader.exec_module(pred)

SERIES = ["TODOS", "THEFT", "BATTERY", "CRIMINAL DAMAGE", "ASSAULT", "DECEPTIVE PRACTICE",
          "MOTOR VEHICLE THEFT", "ROBBERY", "BURGLARY"]
ANOS_TESTE = range(2018, 2025)
JANELA = 4
N_ARVORES, LAGS = 200, 14

df = dl.load_all()
linhas, previsoes = [], {}

def naive_sazonal(treino, teste):
    """Mesmo dia da semana do ano anterior (t-364); se cair fora do treino, usa t-728."""
    out = []
    for t in teste.index:
        for d in (364, 728):
            ref = t - pd.Timedelta(days=d)
            if ref in treino.index:
                out.append(treino[ref]); break
        else:
            out.append(treino.iloc[-365:].mean())
    return pd.Series(out, index=teste.index, dtype=float)

t_ini = time.time()
for serie_nome in SERIES:
    sub = df if serie_nome == "TODOS" else df[df["Primary Type"] == serie_nome]
    serie = pred.serie_diaria(sub)
    for T in ANOS_TESTE:
        treino = serie[(serie.index.year >= T - JANELA) & (serie.index.year <= T - 1)]
        teste = serie[serie.index.year == T]
        if len(treino) < 365 or teste.empty:
            continue
        modelos = {}
        try:
            _, _, modelos["Prophet"] = pred.rodar_prophet(treino, teste, "multiplicative", True)
        except Exception as e:
            print("Prophet falhou", serie_nome, T, e)
        _, modelos["RF recursivo"], _ = pred.rodar_random_forest(treino, teste, N_ARVORES, LAGS, True)
        _, modelos["RF 1 passo"], _ = pred.rodar_random_forest(treino, teste, N_ARVORES, LAGS, False)
        modelos["Média último ano"] = pd.Series(treino[treino.index.year == T - 1].mean(), index=teste.index)
        modelos["Naive sazonal (t-364)"] = naive_sazonal(treino, teste)
        previsoes[(serie_nome, T)] = {"real": teste, **modelos}
        for nome, yh in modelos.items():
            m = pred.calcular_metricas(teste.values, yh.values)
            linhas.append(dict(serie=serie_nome, ano_teste=T, modelo=nome, media_real=teste.mean(),
                               MAE=m["MAE"], RMSE=m["RMSE"], MAPE=m["MAPE"], sMAPE=m["sMAPE"], dias_zero=m["dias_zero"]))
        print(f"{serie_nome:20s} {T}  " + "  ".join(f"{k}={pred.calcular_metricas(teste.values, v.values)['MAE']:.1f}" for k, v in modelos.items()), f"[{time.time()-t_ini:.0f}s]", flush=True)
        pd.DataFrame(linhas).to_csv(os.path.join(AQUI, "resultados", "metricas.csv"), index=False)
        with open(os.path.join(AQUI, "resultados", "previsoes.pkl"), "wb") as f:
            pickle.dump(previsoes, f)
print("FIM", f"{time.time()-t_ini:.0f}s")
