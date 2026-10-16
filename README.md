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
- **Predição de crimes:** comparação entre Prophet e Random Forest recursivo.
- **Análise espacial:** mapas interativos, distritos e identificação de hotspots.

## Estrutura

```text
chicago-crimes-analytics/
├── app.py                    # página inicial do Streamlit
├── data_loader.py            # leitura, filtros de período e cache dos dados
├── pages/                    # quatro páginas de análise
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

## Deploy no Streamlit Community Cloud

1. Selecione o repositório `jrybarczyk/chicago-crimes-analytics` e a branch `main`.
2. Informe `app.py` como **Main file path**.
3. Selecione Python 3.12 nas opções de ambiente.

As dependências estão em `requirements.txt` e a configuração em `.streamlit/`.
Em um deploy existente, atualize o caminho antigo `Codigo_VS_code/app.py` para
`app.py`.

## Autoria e licença

Veja [CITATION.cff](CITATION.cff) para citar o software e
[CHANGELOG.md](CHANGELOG.md) para o histórico de alterações. O código usa a
[licença MIT](LICENSE); a fonte e os termos dos dados estão em
[data/README.md](data/README.md).
