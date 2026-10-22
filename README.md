# Chicago Crimes Analytics

Dashboard em Streamlit para explorar os crimes registrados em Chicago entre 2014 e
2024. Reúne análises estatísticas, séries temporais, previsão diária com Prophet e
Random Forest e mapas com agrupamento espacial por DBSCAN.

O projeto nasceu do trabalho de conclusão de curso de Matheus Henrique Massuda,
com orientação de José Luiz Rybarczyk Filho (IBB/UNESP). O texto está em
[docs/TCC_Matheus_Massuda.pdf](docs/TCC_Matheus_Massuda.pdf).

## Funcionalidades

- **Análise estatística:** filtros, indicadores e exportação dos dados selecionados.
- **Análise exploratória:** evolução temporal, sazonalidade e valores atípicos.
- **Predição de crimes:** comparação entre Prophet e Random Forest recursivo,
  sempre contra linhas de base (naive sazonal e climatologia por dia da semana).
- **Análise espacial:** mapas interativos, distritos e identificação de hotspots.

## Estrutura

```text
chicago-crimes-analytics/
├── app.py                    # página inicial do Streamlit
├── forecasting.py            # lógica de previsão, sem dependência de interface
├── data_loader.py            # leitura, filtros de período e cache dos dados
├── pages/                    # quatro páginas de análise (só interface)
├── tests/                    # testes, inclusive a salvaguarda contra vazamento
├── experiments/              # avaliação com origem deslizante por linha de comando
├── data/
│   ├── README.md             # fonte, formato e atualização dos dados
│   └── processed/            # seis arquivos Parquet de 2014 a 2024
├── docs/
│   ├── README.md             # documentação do projeto
│   ├── methodology.md        # metodologia de previsão
│   ├── TCC_Matheus_Massuda.pdf
│   └── references/tcc.txt    # referências originais do TCC
├── .streamlit/config.toml    # configuração visual e do servidor
├── .devcontainer/            # ambiente para VS Code / Codespaces
├── .python-version           # Python 3.12
├── requirements.txt          # dependências da aplicação
├── requirements-dev.txt      # dependências de desenvolvimento (pytest)
├── CITATION.cff               # autores e citação
├── CHANGELOG.md               # histórico de mudanças
└── LICENSE                    # licença MIT do código
```

## Executar localmente

Com Python 3.12, execute na raiz do repositório:

```bash
git clone https://github.com/jrybarczyk/chicago-crimes-analytics.git
cd chicago-crimes-analytics
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

No Windows, ative o ambiente com `.venv\Scripts\activate`.
Abra o endereço exibido no terminal (por padrão, `http://localhost:8501`).
Os dados Parquet já estão incluídos no repositório.

## Dados e metodologia

Os dados vêm do portal da cidade de Chicago e estão organizados por período em
`data/processed/`. Consulte [data/README.md](data/README.md) para conhecer o formato
esperado e converter novos CSVs.

A comparação dos modelos usa treino anterior ao ano de teste e previsão recursiva
sem acesso aos valores reais futuros. As métricas e os critérios estão em
[docs/methodology.md](docs/methodology.md).

A lógica de previsão vive em `forecasting.py` e não importa Streamlit, de modo que
os resultados publicados podem ser reproduzidos sem abrir o dashboard:

```bash
python -m pip install -r requirements-dev.txt
pytest tests/ -v
python experiments/run_rolling_origin.py --saida resultados/rolling.csv
```

O script avalia cinco tipos de crime em sete anos de teste (35 origens),
comparando Prophet, Random Forest nos dois horizontes e as duas linhas de base, e
grava um CSV por origem. A variável `CHICAGO_DATA_DIR` permite apontar para outra
pasta de dados.

## Deploy no Streamlit Community Cloud

1. Selecione o repositório `jrybarczyk/chicago-crimes-analytics` e a branch `main`.
2. Informe `app.py` como **Main file path**.
3. Selecione Python 3.12 nas opções de ambiente.

As dependências estão em `requirements.txt` e a configuração em `.streamlit/`.
Em um deploy existente, atualize o caminho antigo `Codigo_VS_code/app.py` para
`app.py`.

### Memória

O Community Cloud garante 690 MB de memória por aplicação (o teto de 2,7 GB não
é garantia) e de 0,078 a 2 núcleos de CPU — e a documentação avisa que esses
limites podem mudar sem aviso. Por isso o carregamento é deliberadamente
econômico: as páginas escolhem o período antes de carregar e `data_loader` lê só
as colunas que a aplicação referencia.

Medições do processo com a pilha da aplicação importada (237 MB só de imports):

| Cenário | RSS |
|---|---|
| `load_all(colunas="todas")` — comportamento anterior | 741 MB |
| `load_all()` — 11 anos, colunas da aplicação | 575 MB |
| O que as páginas fazem (triênio, colunas da aplicação) | **347 MB** |
| Caminho completo de predição, com Prophet e Random Forest ajustados | **377 MB** |

Reproduza com `python experiments/medir_memoria.py`. Duas regras para não
regredir: **não** chame `load_all()` em página interativa e **não** troque
`@st.cache_resource` por `@st.cache_data` no carregador — `cache_data` devolve
uma cópia nova a cada chamada e duplica o maior objeto da aplicação.

### Desempenho

Com um núcleo, o caminho de predição leva cerca de 7 s (ajuste do Random Forest
2,0 s mais 4,9 s do laço recursivo de 365 dias; Prophet 0,6 s). Num container de
0,078 a 2 núcleos, conte com mais. As previsões ficam em cache por configuração,
então repetir a mesma seleção é instantâneo. Aplicações sem tráfego por 12 horas
hibernam: o primeiro acesso depois disso paga o carregamento inteiro.

## Autoria e licença

Veja [CITATION.cff](CITATION.cff) para citar o software e
[CHANGELOG.md](CHANGELOG.md) para o histórico de alterações. O código usa a
[licença MIT](LICENSE); a fonte e os termos dos dados estão em
[data/README.md](data/README.md).
