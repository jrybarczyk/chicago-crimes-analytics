#!/usr/bin/env python
"""experiments/run_rolling_origin.py - Avaliação com origem deslizante.

Produz o CSV que sustenta as tabelas do artigo, sem depender do dashboard.
Para cada tipo de crime e cada ano de teste, treina nos N anos imediatamente
anteriores e avalia no ano seguinte, comparando:

    Prophet (multi-passo)            previsão do ano inteiro, sem ver o teste
    Random Forest recursivo          idem, realimentando as próprias previsões
    Random Forest 1 passo à frente   conhece o dia anterior observado
    Naive sazonal (m = 7)            última semana do treino, repetida
    Climatologia por dia da semana   média por dia da semana do último ano

Os dois primeiros são os únicos comparáveis entre si. O terceiro responde a
outra pergunta (dimensionar o dia seguinte) e é reportado separadamente. As
duas linhas de base existem para que se saiba quanto do desempenho vem do
modelo e quanto da estrutura sazonal.

Uso:
    python experiments/run_rolling_origin.py
    python experiments/run_rolling_origin.py --crimes THEFT ASSAULT --anos 2019 2024
    python experiments/run_rolling_origin.py --saida resultados/rolling.csv
"""
import argparse
import glob
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import forecasting as fc  # noqa: E402
from data_loader import DATA_DIR, ANO_MIN, ANO_MAX  # noqa: E402

CRIMES_PADRAO = ["THEFT", "BATTERY", "CRIMINAL DAMAGE", "ASSAULT", "MOTOR VEHICLE THEFT"]
LIMIAR_QUEBRA = 15.0  # % de variação do nível médio que define quebra de regime


def carregar(colunas=("Date", "Primary Type", "Year")):
    """Lê os Parquet direto, sem passar pelo Streamlit."""
    arquivos = sorted(glob.glob(os.path.join(DATA_DIR, "chicago_crimes_*.parquet")))
    if not arquivos:
        raise SystemExit(f"Nenhum Parquet encontrado em {DATA_DIR}. "
                         "Defina CHICAGO_DATA_DIR ou gere os arquivos (ver data/README.md).")
    df = pd.concat([pd.read_parquet(f, columns=list(colunas)) for f in arquivos],
                   ignore_index=True)
    df["Primary Type"] = df["Primary Type"].astype("category")
    return df.dropna(subset=["Date"]).reset_index(drop=True)


def avaliar_origem(serie_crime, ano_teste, anos_treino, n_jobs=-1):
    t0, t1 = ano_teste - anos_treino, ano_teste - 1
    sub = serie_crime[serie_crime["Year"].between(t0, ano_teste)]
    s = fc.serie_diaria(sub)
    treino = s[(s.index.year >= t0) & (s.index.year <= t1)]
    teste = s[s.index.year == ano_teste]
    if len(treino) < 365 or len(teste) < 300:
        return []

    previsoes = {}
    previsoes["Prophet"] = fc.rodar_prophet(treino, teste)[2]
    previsoes["RF (recursivo)"] = fc.rodar_random_forest(treino, teste, modo_recursivo=True,
                                                         n_jobs=n_jobs)[0]
    previsoes["RF (1 passo)"] = fc.rodar_random_forest(treino, teste, modo_recursivo=False,
                                                       n_jobs=n_jobs)[0]
    previsoes["Naive sazonal"] = fc.naive_sazonal(treino, teste)
    previsoes["Climatologia"] = fc.climatologia(treino, teste)

    delta = float((teste.mean() / treino.mean() - 1) * 100)
    linhas = []
    for nome, prev in previsoes.items():
        m = fc.calcular_metricas(teste.values, prev.values)
        m.update({
            "ano_teste": ano_teste, "modelo": nome, "treino": f"{t0}-{t1}",
            "media_treino": float(treino.mean()), "media_teste": float(teste.mean()),
            "delta_nivel_pct": delta,
            "regime": "quebra" if abs(delta) >= LIMIAR_QUEBRA else "estavel",
        })
        linhas.append(m)
    return linhas


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crimes", nargs="+", default=CRIMES_PADRAO)
    ap.add_argument("--anos", nargs=2, type=int, metavar=("PRIMEIRO", "ULTIMO"),
                    default=[ANO_MIN + 4, ANO_MAX],
                    help="intervalo de anos de TESTE (padrão: do 5º ano da base ao último)")
    ap.add_argument("--anos-treino", type=int, default=4,
                    help="quantos anos imediatamente anteriores compõem o treino")
    ap.add_argument("--saida", default="rolling_origin_resultados.csv")
    ap.add_argument("--n-jobs", type=int, default=-1,
                    help="núcleos para o Random Forest. Use 1 em containers que restringem "
                         "pools de threads (o resultado não muda: random_state é fixo).")
    args = ap.parse_args()

    df = carregar()
    linhas, t0 = [], time.time()
    for crime in args.crimes:
        sub = df[df["Primary Type"] == crime]
        if sub.empty:
            print(f"  (sem registros para {crime}, pulando)", flush=True)
            continue
        for ano in range(args.anos[0], args.anos[1] + 1):
            novas = avaliar_origem(sub, ano, args.anos_treino, args.n_jobs)
            for n in novas:
                n["crime"] = crime
            linhas.extend(novas)
            print(f"  {crime} {ano}: {'ok' if novas else 'dados insuficientes'} "
                  f"({time.time() - t0:.0f}s)", flush=True)

    if not linhas:
        raise SystemExit("Nenhuma origem pôde ser avaliada.")

    colunas = ["crime", "ano_teste", "treino", "modelo", "regime", "MAE", "RMSE", "MSE",
               "ME", "MAPE", "sMAPE", "media_treino", "media_teste", "delta_nivel_pct",
               "dias_zero"]
    out = pd.DataFrame(linhas)[colunas]
    os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    out.to_csv(args.saida, index=False, encoding="utf-8")

    n_origens = out.groupby(["crime", "ano_teste"]).ngroups
    print(f"\n{len(out)} linhas, {n_origens} origens -> {args.saida}")
    print("\nMediana do MAPE por modelo e regime:")
    print(out.pivot_table(index="modelo", columns="regime", values="MAPE",
                          aggfunc="median").round(2).to_string())
    print("\nMediana do MAE por modelo e regime:")
    print(out.pivot_table(index="modelo", columns="regime", values="MAE",
                          aggfunc="median").round(2).to_string())


if __name__ == "__main__":
    main()
