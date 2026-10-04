# Consolida paper/resultados/metricas.csv em tabelas para o manuscrito e aplica o
# teste de Diebold-Mariano (Prophet × RF recursivo) em cada cenário.
# Saída: paper/resultados/tabelas.md (Markdown) e tabelas CSV individuais.
import os, pickle
import numpy as np, pandas as pd
from scipy import stats

AQUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(AQUI, "resultados")
met = pd.read_csv(os.path.join(RES, "metricas.csv"))
with open(os.path.join(RES, "previsoes.pkl"), "rb") as f:
    prev = pickle.load(f)

MODELOS = ["Prophet", "RF recursivo", "RF 1 passo", "Média último ano", "Naive sazonal (t-364)"]
MULTI = ["Prophet", "RF recursivo", "Média último ano", "Naive sazonal (t-364)"]  # previsão multi-passo genuína
ORDEM = ["TODOS", "THEFT", "BATTERY", "CRIMINAL DAMAGE", "ASSAULT", "DECEPTIVE PRACTICE",
         "MOTOR VEHICLE THEFT", "ROBBERY", "BURGLARY"]
met["modelo"] = pd.Categorical(met["modelo"], MODELOS, ordered=True)
met["serie"] = pd.Categorical(met["serie"], ORDEM, ordered=True)

# MAE relativo ao ingênuo sazonal (escala comparável entre séries de magnitudes distintas)
base = met[met["modelo"] == "Naive sazonal (t-364)"].set_index(["serie", "ano_teste"])["MAE"]
met["MAE_rel"] = met.apply(lambda r: r["MAE"] / base.loc[(r["serie"], r["ano_teste"])], axis=1)

saida = []
def tabela(titulo, df_):
    saida.append(f"\n### {titulo}\n\n" + df_.to_markdown() + "\n")

# T1: média geral por modelo (todas as séries e anos)
geral = met.groupby("modelo", observed=True).agg(
    MAE_rel=("MAE_rel", "mean"), sMAPE=("sMAPE", "mean"), MAPE=("MAPE", "mean")).round(3)
vit = met[met["modelo"].isin(MULTI)].sort_values("MAE").groupby(["serie", "ano_teste"], observed=True).first()["modelo"].value_counts()
geral["vitorias_multi_passo"] = vit.reindex(geral.index).fillna(0).astype(int)
tabela("T1. Desempenho médio (63 cenários = 9 séries × 7 anos de teste)", geral)
geral.to_csv(os.path.join(RES, "t1_geral.csv"))

# T2: por ano de teste (média entre séries), só multi-passo
por_ano = met[met["modelo"].isin(MULTI)].pivot_table(index="ano_teste", columns="modelo", values="MAE_rel", aggfunc="mean", observed=True).round(2)
tabela("T2. MAE relativo ao ingênuo sazonal, por ano de teste (média das 9 séries)", por_ano)
por_ano.to_csv(os.path.join(RES, "t2_por_ano.csv"))

# T3: por série (média entre anos), só multi-passo
por_serie = met[met["modelo"].isin(MULTI)].pivot_table(index="serie", columns="modelo", values="MAE_rel", aggfunc="mean", observed=True).round(2)
por_serie["média real/dia"] = met.groupby("serie", observed=True)["media_real"].mean().round(1)
tabela("T3. MAE relativo ao ingênuo sazonal, por série (média dos 7 anos)", por_serie)
por_serie.to_csv(os.path.join(RES, "t3_por_serie.csv"))

# T4: anos "normais" (2018, 2019, 2023, 2024) vs anos de ruptura (2020, 2021, 2022)
met["regime"] = np.where(met["ano_teste"].isin([2020, 2021, 2022]), "ruptura (2020–2022)", "estável (2018–19, 2023–24)")
regime = met[met["modelo"].isin(MULTI)].pivot_table(index="regime", columns="modelo", values=["MAE_rel", "sMAPE"], aggfunc="mean", observed=True).round(2)
tabela("T4. Regime estável × ruptura (média das 9 séries)", regime)
regime.to_csv(os.path.join(RES, "t4_regime.csv"))

# T5: sMAPE completo por série e ano para Prophet e RF recursivo
for modelo in ["Prophet", "RF recursivo"]:
    t = met[met["modelo"] == modelo].pivot_table(index="serie", columns="ano_teste", values="sMAPE", observed=True).round(1)
    tabela(f"T5. sMAPE (%) — {modelo}", t)
    t.to_csv(os.path.join(RES, f"t5_smape_{modelo.replace(' ', '_')}.csv"))

# Diebold-Mariano: Prophet vs RF recursivo, perda absoluta, h=1 (HAC Newey-West com 7 lags)
def dm_test(e1, e2, lags=7):
    d = np.abs(e1) - np.abs(e2)
    n = len(d); dbar = d.mean()
    gamma = [np.sum((d[k:] - dbar) * (d[:n - k] - dbar)) / n for k in range(lags + 1)]
    var = (gamma[0] + 2 * sum((1 - k / (lags + 1)) * gamma[k] for k in range(1, lags + 1))) / n
    stat = dbar / np.sqrt(var)
    return stat, 2 * (1 - stats.norm.cdf(abs(stat)))

linhas = []
for (serie, T), p in prev.items():
    real = p["real"].values
    s, pv = dm_test(real - p["Prophet"].values, real - p["RF recursivo"].values)
    linhas.append(dict(serie=serie, ano_teste=T, DM=round(s, 2), p=round(pv, 4),
                       melhor="RF recursivo" if s > 0 else "Prophet", significativo=pv < 0.05))
dm = pd.DataFrame(linhas)
dm["serie"] = pd.Categorical(dm["serie"], ORDEM, ordered=True); dm = dm.sort_values(["serie", "ano_teste"])
dm.to_csv(os.path.join(RES, "diebold_mariano.csv"), index=False)
resumo_dm = dm.groupby(["melhor", "significativo"]).size().unstack(fill_value=0)
tabela("T6. Teste de Diebold-Mariano (Prophet × RF recursivo), contagem de cenários", resumo_dm)
tabela("T6b. Detalhe por cenário", dm.set_index(["serie", "ano_teste"]))

# Cenários do TCC
tcc = met[((met["serie"] == "ASSAULT") & (met["ano_teste"] == 2018)) | ((met["serie"] == "THEFT") & (met["ano_teste"] == 2021))]
tabela("T7. Cenários do TCC (MAE, RMSE, MAPE, sMAPE)", tcc.set_index(["serie", "ano_teste", "modelo"])[["MAE", "RMSE", "MAPE", "sMAPE"]].round(2))

with open(os.path.join(RES, "tabelas.md"), "w") as f:
    f.write("# Tabelas consolidadas do experimento com origem deslizante\n" + "".join(saida))
print("".join(saida))
