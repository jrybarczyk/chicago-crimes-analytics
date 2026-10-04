# chicago-crime-analytics

Dashboard em Streamlit e material de pesquisa para análise estatística, exploratória,
preditiva e espacial dos crimes registrados em Chicago (2014–2024). O projeto nasceu
como trabalho de conclusão de curso de Matheus Henrique Massuda
(`TCC_Matheus_Massuda.pdf`, orientação de José Luiz Rybarczyk Filho, IBB/UNESP) e foi
ampliado para publicação: avaliação com origem deslizante em 63 cenários, baselines
ingênuas e comparação estatística entre modelos.

**Principais resultados** (detalhes em `paper/`):

- Prophet e Random Forest recursivo são equivalentes na média dos 63 cenários e
  reduzem o erro do ingênuo sazonal em cerca de 11%.
- Em anos estáveis o Prophet é melhor; em anos de ruptura (pandemia) ele extrapola
  tendências e falha, e o Random Forest se equipara a uma baseline de nível recente.
- O padrão semanal depende do tipo de crime, e a base contém um artefato de horário
  padrão (12:00 e 00:00) que afeta análises sub-diárias.

## Estrutura

```
paper/
├── manuscrito.md                 # texto do artigo (fonte)
├── gerar_docx.py                 # gera o .docx no template da Rev. Bras. Crim.
├── experimento_rolling.py        # avaliação com origem deslizante (63 cenários)
├── analise_resultados.py         # tabelas e teste de Diebold-Mariano
├── figuras.py                    # figuras do artigo (PNG 300 dpi + PDF)
├── figuras/ · resultados/        # saídas versionadas
└── template/                     # template oficial da revista
Codigo_VS_code/
├── app.py                        # página inicial
├── data_loader.py                # carregamento centralizado dos CSVs (com cache)
├── pages/
│   ├── 01_analise_estatistica.py # filtros, métricas e exportação
│   ├── 02_analise_exploratoria.py# série temporal, sazonalidade, outliers
│   ├── 03_predicao_crimes.py     # Prophet × Random Forest (previsão diária)
│   └── 04_analise_espacial.py    # mapas Folium, distritos, DBSCAN
├── data_splits/                  # dados em Parquet (um arquivo por período)
└── requirements.txt
```

## Como rodar

```bash
cd Codigo_VS_code
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Dados

Os dados estão em `Codigo_VS_code/data_splits/`, em formato Parquet (zstd), um
arquivo por período, ~92 MB no total:

```
chicago_crimes_2014_2015.parquet
chicago_crimes_2016_2017.parquet
chicago_crimes_2018_2019.parquet
chicago_crimes_2020_2021.parquet
chicago_crimes_2022_2023.parquet
chicago_crimes_2024_2024.parquet
```

Fonte: portal de dados da cidade de Chicago, *Crimes - 2001 to Present*
(https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2).

Para atualizar ou regenerar, coloque CSVs com o nome
`chicago_crimes_<ano_inicial>_<ano_final>.csv` na mesma pasta e rode:

```bash
cd Codigo_VS_code && python data_loader.py
```

O loader aceita CSV e Parquet; quando os dois existem para o mesmo período, usa o
Parquet. Colunas esperadas: `ID, Date, IUCR, Primary Type, Description, Arrest,
Domestic, Beat, District, Ward, Community Area, FBI Code, X Coordinate,
Y Coordinate, Year, Latitude, Longitude, Month, Day, Hour, DayOfWeek`, com `Date`
no formato `AAAA-MM-DD HH:MM:SS`.

## Deploy no Streamlit Community Cloud

1. Suba o repositório no GitHub.
2. Em https://share.streamlit.io, clique em **Create app** e selecione o repositório.
3. Em **Main file path** informe `Codigo_VS_code/app.py`.
4. A versão do Python vem de `.python-version` (3.12) e as dependências de
   `requirements.txt` na raiz. Nada mais precisa ser configurado.

O primeiro carregamento lê os Parquets (cerca de 1 s) e mantém o dataset em cache;
o uso de memória fica em torno de 250 MB, dentro do limite do plano gratuito.

## Metodologia de previsão

Prophet e Random Forest recebem a mesma série diária (dias sem ocorrência contam
como zero) e são avaliados no mesmo ano de teste, sempre o ano seguinte ao fim do
treino. As features de lag e média móvel do Random Forest usam apenas valores
anteriores ao dia previsto, e o modo recursivo gera a previsão do ano inteiro sem
acesso aos valores reais do teste, tornando-a comparável à do Prophet.
Métricas: MAE, RMSE, MAPE (dias com valor > 0) e sMAPE.

## Reproduzir o artigo

```bash
source .venv/bin/activate
python paper/experimento_rolling.py   # ~25 min; gera paper/resultados/
python paper/analise_resultados.py    # tabelas consolidadas e teste DM
python paper/figuras.py               # figuras em paper/figuras/
python paper/gerar_docx.py            # paper/saida/*.docx (versões anônima e identificada)
```

## Como citar

Veja `CITATION.cff`. Licença MIT (`LICENSE`). Histórico de mudanças em `CHANGELOG.md`.
