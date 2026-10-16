# Dados

Fonte: portal de dados da cidade de Chicago, conjunto
[Crimes - 2001 to Present](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2).
Consulte o portal de origem para os termos de uso e a descrição dos campos.

## Arquivos versionados

A pasta `processed/` contém os dados usados pelo dashboard, em Parquet com
compressão zstd, organizados nos períodos 2014–2015, 2016–2017, 2018–2019,
2020–2021, 2022–2023 e 2024. Os CSVs não são versionados.

O carregamento resolve os caminhos a partir de `data_loader.py`, sem depender do
diretório de trabalho, e prioriza Parquet quando há um CSV do mesmo período.

## Converter CSVs

Coloque os arquivos preparados em `data/processed/`, com nomes no padrão
`chicago_crimes_<ano_inicial>_<ano_final>.csv`, e execute na raiz:

```bash
python data_loader.py
```

Esse comando converte os CSVs existentes para Parquet; ele não baixa nem prepara
os arquivos brutos do portal. Arquivos Parquet do mesmo período são sobrescritos.

Campos usados pela aplicação:

```text
ID, Date, IUCR, Primary Type, Description, Arrest, Domestic, Beat,
District, Ward, Community Area, FBI Code, X Coordinate, Y Coordinate,
Year, Latitude, Longitude, Month, Day, Hour, DayOfWeek
```

A coluna `Date` deve estar no formato `AAAA-MM-DD HH:MM:SS`. O carregador pode
derivar `Year`, `Month` e `Hour` a partir dela quando essas colunas não existem.
Para ampliar o intervalo além de 2014–2024, ajuste também `ANO_MIN`, `ANO_MAX` e
os seletores de período da aplicação.
