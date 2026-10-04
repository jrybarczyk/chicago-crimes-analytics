# Gera as figuras do manuscrito em paper/figuras/ (PNG 300 dpi + PDF).
# Normas RBC: cores sólidas legíveis em P&B, moldura nos quatro lados com marcas de
# escala em todos os lados, rótulos legíveis. Uso: python paper/figuras.py
import os, sys, pickle, warnings
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

warnings.filterwarnings("ignore")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, "..", "Codigo_VS_code")
FIG = os.path.join(AQUI, "figuras")
RES = os.path.join(AQUI, "resultados")
os.makedirs(FIG, exist_ok=True)
sys.path.insert(0, RAIZ)
import data_loader as dl

# Paleta Okabe-Ito (segura para daltonismo, distinguível em P&B pela luminância)
C = {"azul": "#0072B2", "laranja": "#E69F00", "verde": "#009E73", "vermelho": "#D55E00",
     "roxo": "#CC79A7", "ceu": "#56B4E9", "amarelo": "#F0E442", "preto": "#000000", "cinza": "#8C8C8C"}
MODELO_COR = {"Real": C["preto"], "Prophet": C["azul"], "RF recursivo": C["vermelho"],
              "RF 1 passo": C["laranja"],               "Média último ano": C["cinza"], "Naive sazonal (t-364)": C["verde"]}

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif", "Liberation Serif"],
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.linewidth": 0.8,
    "xtick.direction": "in", "ytick.direction": "in", "xtick.top": True, "ytick.right": True,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5, "legend.frameon": False,
    "figure.dpi": 100, "savefig.dpi": 300, "savefig.bbox": "tight",
})
LARGURA_COLUNA, LARGURA_PAGINA = 3.3, 6.9  # polegadas (RBC: duas colunas em A4)


def salvar(fig, nome):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, f"{nome}.{ext}"))
    plt.close(fig)
    print("ok", nome)


df = dl.load_all()

# ---------------------------------------------------------------- Fig 1: série anual
anual = df.groupby("Year").size()
fig, ax = plt.subplots(figsize=(LARGURA_COLUNA, 2.3))
ax.axvspan(2019.5, 2021.5, color=C["cinza"], alpha=0.18, lw=0)
ax.text(2020.5, 298, "pandemia", ha="center", va="top", fontsize=7.5, color="#444")
ax.plot(anual.index, anual.values / 1000, "-o", color=C["azul"], lw=1.6, ms=4)
for a, v in anual.items():
    if a in (2014, 2019, 2020, 2023, 2024):
        ax.annotate(f"{v/1000:.0f}", (a, v / 1000), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7)
ax.set_xlabel("Ano"); ax.set_ylabel("Crimes registrados (milhares)")
ax.set_xticks(list(anual.index)); ax.tick_params(axis="x", labelrotation=45)
ax.set_ylim(180, 300)
salvar(fig, "fig01_serie_anual")

# ---------------------------------------------------------------- Fig 2: distribuição horária e artefato
df["_min"] = df["Date"].dt.minute
h_total = df["Hour"].value_counts().sort_index()
h_sem00 = df.loc[df["_min"] != 0, "Hour"].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(LARGURA_COLUNA, 2.3))
ax.bar(h_total.index - 0.2, h_total.values / 1000, width=0.4, color=C["ceu"], label="Todos os registros")
ax.bar(h_sem00.index + 0.2, h_sem00.values / 1000, width=0.4, color=C["azul"], label="Excluindo minuto :00")
ax.set_xlabel("Hora do dia"); ax.set_ylabel("Registros (milhares)")
ax.set_xticks(range(0, 24, 2)); ax.set_ylim(0, 215); ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
salvar(fig, "fig02_distribuicao_horaria")

# ---------------------------------------------------------------- Fig 3: dia da semana por tipo (índice = 100)
DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
series_dow = {"Todos os crimes": df, "THEFT (furto)": df[df["Primary Type"] == "THEFT"],
              "BATTERY (agressão)": df[df["Primary Type"] == "BATTERY"],
              "ASSAULT (ameaça)": df[df["Primary Type"] == "ASSAULT"]}
fig, axes = plt.subplots(1, 4, figsize=(LARGURA_PAGINA, 2.0), sharey=True)
fig.subplots_adjust(wspace=0.12)
for ax, (nome, sub) in zip(axes, series_dow.items()):
    d = sub.resample("D", on="Date").size()
    m = d.groupby(d.index.dayofweek).mean()
    idx = m / m.mean() * 100
    cores = [C["laranja"] if i >= 5 else C["azul"] for i in range(7)]
    ax.bar(range(7), idx.values, color=cores, width=0.7)
    ax.axhline(100, color=C["preto"], lw=0.8, ls="--")
    ax.set_xticks(range(7)); ax.set_xticklabels(DIAS, fontsize=6.5, rotation=60)
    ax.set_title(nome, fontsize=8); ax.set_ylim(85, 125)
    ax.text(6.4, 123, f"{idx.values[5:].mean()-idx.values[:5].mean():+.1f} fim de semana", ha="right", va="top", fontsize=6.5)
axes[0].set_ylabel("Índice (média = 100)")
salvar(fig, "fig03_dia_semana_por_tipo")

# ---------------------------------------------------------------- Fig 4: sazonalidade mensal
d_all = df.resample("D", on="Date").size()
mes = d_all.groupby(d_all.index.month).mean()
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
fig, ax = plt.subplots(figsize=(LARGURA_COLUNA, 2.2))
ax.plot(range(1, 13), mes.values, "-o", color=C["azul"], lw=1.6, ms=4)
ax.set_xticks(range(1, 13)); ax.set_xticklabels(MESES, fontsize=7)
ax.set_ylabel("Média de crimes por dia"); ax.set_xlabel("Mês")
ax.annotate(f"máx. {mes.max():.0f}", (mes.idxmax(), mes.max()), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=7)
ax.annotate(f"mín. {mes.min():.0f}", (mes.idxmin(), mes.min()), xytext=(0, -11), textcoords="offset points", ha="center", fontsize=7)
ax.set_ylim(mes.min() * 0.93, mes.max() * 1.05)
salvar(fig, "fig04_sazonalidade_mensal")

# ---------------------------------------------------------------- Fig 7: hotspots DBSCAN (ASSAULT 2024)
from sklearn.cluster import DBSCAN
EPS_M, MIN_PTS = 200, 30
sub = df[(df["Primary Type"] == "ASSAULT") & (df["Year"] == 2024)].dropna(subset=["Latitude", "Longitude"])
sub = sub[sub["Latitude"].between(41.6, 42.1) & sub["Longitude"].between(-88.0, -87.5)]
rng = np.random.default_rng(42)
amostra = sub.sample(n=min(30000, len(sub)), random_state=42)
coords = amostra[["Latitude", "Longitude"]].to_numpy()
labels = DBSCAN(eps=EPS_M / 6_371_000, min_samples=MIN_PTS, metric="haversine", algorithm="ball_tree").fit_predict(np.radians(coords))
tam = pd.Series(labels[labels != -1]).value_counts()
fig, ax = plt.subplots(figsize=(LARGURA_COLUNA, 3.6))
ruido = labels == -1
ax.scatter(coords[ruido, 1], coords[ruido, 0], s=1.5, color="#BBBBBB", lw=0, label=f"Ruído ({ruido.mean()*100:.0f}%)")
paleta = [C["azul"], C["vermelho"], C["verde"], C["laranja"], C["roxo"], C["ceu"], C["amarelo"], C["preto"]]
for i, (cid, n) in enumerate(tam.head(8).items()):
    m = labels == cid
    ax.scatter(coords[m, 1], coords[m, 0], s=3, color=paleta[i], lw=0, label=f"C{i+1} (n={n})")
outros = np.isin(labels, tam.index[8:])
if outros.any():
    ax.scatter(coords[outros, 1], coords[outros, 0], s=2, color="#555555", lw=0, label=(f"Outros {len(tam)-8} clusters" if len(tam)-8 > 1 else "Outro cluster"))
ax.set_aspect(1 / np.cos(np.radians(41.85)))
ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
ax.legend(loc="lower left", fontsize=6.5, markerscale=3, ncol=1)
ax.set_title(f"ASSAULT 2024 — DBSCAN (raio {EPS_M} m, mín. {MIN_PTS} pontos): {len(tam)} clusters", fontsize=8)
salvar(fig, "fig07_hotspots_dbscan")

# ---------------------------------------------------------------- Figuras que dependem do experimento
pkl = os.path.join(RES, "previsoes.pkl")
if not os.path.exists(pkl):
    print("previsoes.pkl ausente; figuras 5 e 6 não geradas"); sys.exit()
with open(pkl, "rb") as f:
    prev = pickle.load(f)

def painel_previsao(ax, chave, titulo):
    p = prev[chave]; real = p["real"]
    # semanal (média móvel de 7 dias) para legibilidade
    def sm(x): return x.rolling(7, center=True).mean()
    ax.plot(real.index, sm(real), color=MODELO_COR["Real"], lw=1.4, label="Real")
    ax.plot(real.index, sm(p["Prophet"]), color=MODELO_COR["Prophet"], lw=1.2, label="Prophet")
    ax.plot(real.index, sm(p["RF recursivo"]), color=MODELO_COR["RF recursivo"], lw=1.2, ls="--", label="RF recursivo")
    ax.set_title(titulo, fontsize=8.5); ax.set_ylabel("Crimes/dia (média móvel 7 d)")
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))

fig, axes = plt.subplots(1, 2, figsize=(LARGURA_PAGINA, 2.4))
if ("ASSAULT", 2018) in prev:
    painel_previsao(axes[0], ("ASSAULT", 2018), "(a) ASSAULT 2018 (treino 2014–2017)")
if ("THEFT", 2021) in prev:
    painel_previsao(axes[1], ("THEFT", 2021), "(b) THEFT 2021 (treino 2017–2020, pandemia)")
axes[0].legend(loc="lower right", ncol=1, fontsize=7)
salvar(fig, "fig05_previsao_vs_real")

# Fig 6: heatmap MAE_modelo / MAE_naive sazonal (<1 = melhor que o ingênuo)
met = pd.read_csv(os.path.join(RES, "metricas.csv"))
base = met[met["modelo"] == "Naive sazonal (t-364)"].set_index(["serie", "ano_teste"])["MAE"]
ordem_series = ["TODOS", "THEFT", "BATTERY", "CRIMINAL DAMAGE", "ASSAULT", "DECEPTIVE PRACTICE", "MOTOR VEHICLE THEFT", "ROBBERY", "BURGLARY"]
fig, axes = plt.subplots(1, 2, figsize=(LARGURA_PAGINA, 3.0), sharey=True)
for ax, modelo in zip(axes, ["Prophet", "RF recursivo"]):
    m = met[met["modelo"] == modelo].set_index(["serie", "ano_teste"])["MAE"]
    razao = (m / base).unstack("ano_teste").reindex(ordem_series)
    im = ax.imshow(razao.values, cmap="RdBu_r", vmin=0.4, vmax=1.6, aspect="auto")
    ax.set_xticks(range(razao.shape[1])); ax.set_xticklabels(razao.columns, fontsize=7.5)
    ax.set_yticks(range(razao.shape[0])); ax.set_yticklabels(razao.index, fontsize=7.5)
    ax.set_title(modelo, fontsize=9); ax.grid(False)
    for i in range(razao.shape[0]):
        for j in range(razao.shape[1]):
            v = razao.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5, color="white" if abs(v - 1) > 0.35 else "black")
cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02); cb.set_label("MAE / MAE do ingênuo sazonal", fontsize=8)
salvar(fig, "fig06_heatmap_mae_relativo")
