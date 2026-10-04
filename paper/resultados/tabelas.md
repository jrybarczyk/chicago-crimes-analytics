# Tabelas consolidadas do experimento com origem deslizante

### T1. Desempenho médio (63 cenários = 9 séries × 7 anos de teste)

| modelo                |   MAE_rel |   sMAPE |   MAPE |   vitorias_multi_passo |
|:----------------------|----------:|--------:|-------:|-----------------------:|
| Prophet               |     0.886 |  23.604 | 24.808 |                     32 |
| RF recursivo          |     0.89  |  21.302 | 23.287 |                     23 |
| RF 1 passo            |     0.647 |  15.807 | 17.706 |                      0 |
| Média último ano      |     0.905 |  21.718 | 24.3   |                      8 |
| Naive sazonal (t-364) |     1     |  24.554 | 27.017 |                      0 |

### T2. MAE relativo ao ingênuo sazonal, por ano de teste (média das 9 séries)

|   ano_teste |   Prophet |   RF recursivo |   Média último ano |   Naive sazonal (t-364) |
|------------:|----------:|---------------:|-------------------:|------------------------:|
|        2018 |      0.77 |           0.95 |               0.98 |                       1 |
|        2019 |      0.73 |           0.91 |               0.96 |                       1 |
|        2020 |      0.85 |           0.8  |               0.91 |                       1 |
|        2021 |      1.13 |           0.95 |               0.81 |                       1 |
|        2022 |      0.99 |           0.89 |               0.93 |                       1 |
|        2023 |      0.93 |           0.82 |               0.86 |                       1 |
|        2024 |      0.81 |           0.91 |               0.88 |                       1 |

### T3. MAE relativo ao ingênuo sazonal, por série (média dos 7 anos)

| serie               |   Prophet |   RF recursivo |   Média último ano |   Naive sazonal (t-364) |   média real/dia |
|:--------------------|----------:|---------------:|-------------------:|------------------------:|-----------------:|
| TODOS               |      0.79 |           0.97 |               1    |                       1 |            659.9 |
| THEFT               |      0.95 |           1    |               0.96 |                       1 |            147.2 |
| BATTERY             |      0.89 |           0.95 |               1.05 |                       1 |            121.9 |
| CRIMINAL DAMAGE     |      0.76 |           0.82 |               0.91 |                       1 |             74.1 |
| ASSAULT             |      0.82 |           1.03 |               0.89 |                       1 |             57.1 |
| DECEPTIVE PRACTICE  |      1.21 |           0.66 |               0.86 |                       1 |             45.5 |
| MOTOR VEHICLE THEFT |      0.93 |           0.93 |               0.85 |                       1 |             43.6 |
| ROBBERY             |      0.8  |           0.9  |               0.83 |                       1 |             24.4 |
| BURGLARY            |      0.82 |           0.75 |               0.8  |                       1 |             23.5 |

### T4. Regime estável × ruptura (média das 9 séries)

| regime                     |   ('MAE_rel', 'Prophet') |   ('MAE_rel', 'RF recursivo') |   ('MAE_rel', 'Média último ano') |   ('MAE_rel', 'Naive sazonal (t-364)') |   ('sMAPE', 'Prophet') |   ('sMAPE', 'RF recursivo') |   ('sMAPE', 'Média último ano') |   ('sMAPE', 'Naive sazonal (t-364)') |
|:---------------------------|-------------------------:|------------------------------:|----------------------------------:|---------------------------------------:|-----------------------:|----------------------------:|--------------------------------:|-------------------------------------:|
| estável (2018–19, 2023–24) |                     0.81 |                          0.9  |                              0.92 |                                      1 |                  17.41 |                       18.52 |                           18.88 |                                21.47 |
| ruptura (2020–2022)        |                     0.99 |                          0.88 |                              0.88 |                                      1 |                  31.87 |                       25.01 |                           25.5  |                                28.66 |

### T5. sMAPE (%) — Prophet

| serie               |   2018 |   2019 |   2020 |   2021 |   2022 |   2023 |   2024 |
|:--------------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| TODOS               |    6   |    6.7 |   23.2 |   11.7 |   11.3 |   10   |    6.3 |
| THEFT               |    8.2 |   10.9 |   42.1 |   81.5 |   12.2 |   13.3 |    8.9 |
| BATTERY             |   10.1 |   10.4 |   21.1 |   22.7 |   13.8 |   14   |   11.1 |
| CRIMINAL DAMAGE     |   14.3 |   13.1 |   14.6 |   15.4 |   14   |   18.3 |   13.1 |
| ASSAULT             |   12.1 |   13   |   19.3 |   23.3 |   16.6 |   13   |   13.1 |
| DECEPTIVE PRACTICE  |   15.2 |   16   |   35.9 |   67.9 |  155.2 |   25.6 |   20.7 |
| MOTOR VEHICLE THEFT |   19.3 |   18.1 |   28.7 |   23.1 |   46   |   42.3 |   34.4 |
| ROBBERY             |   24   |   22.4 |   26.7 |   24.1 |   22.1 |   25.3 |   41   |
| BURGLARY            |   25.3 |   18.7 |   22.8 |   35.9 |   29.2 |   23.2 |   29.2 |

### T5. sMAPE (%) — RF recursivo

| serie               |   2018 |   2019 |   2020 |   2021 |   2022 |   2023 |   2024 |
|:--------------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| TODOS               |    7.3 |    7   |   22.4 |   19.8 |   14.8 |    7.8 |    9.4 |
| THEFT               |   14.6 |   17.2 |   33.5 |   19.2 |   44.3 |   12.5 |   11.5 |
| BATTERY             |   11.9 |   12.6 |   16.9 |   23.2 |   14.1 |   17.3 |   12.1 |
| CRIMINAL DAMAGE     |   15.6 |   16.4 |   16.2 |   19.2 |   15.2 |   14.1 |   15.9 |
| ASSAULT             |   13.1 |   13.7 |   18.8 |   35.9 |   19.1 |   25.4 |   15.8 |
| DECEPTIVE PRACTICE  |   14.7 |   13.9 |   33.2 |   33   |   21.2 |   18.1 |   16.1 |
| MOTOR VEHICLE THEFT |   24.8 |   25.7 |   19.2 |   18.4 |   59.7 |   21.4 |   43.7 |
| ROBBERY             |   38.4 |   26   |   30.7 |   23.9 |   23   |   29.2 |   33.5 |
| BURGLARY            |   19.9 |   27.5 |   30.7 |   30.6 |   19.1 |   21.1 |   21.8 |

### T6. Teste de Diebold-Mariano (Prophet × RF recursivo), contagem de cenários

| melhor       |   False |   True |
|:-------------|--------:|-------:|
| Prophet      |      10 |     27 |
| RF recursivo |       6 |     20 |

### T6b. Detalhe por cenário

|                               |     DM |      p | melhor       | significativo   |
|:------------------------------|-------:|-------:|:-------------|:----------------|
| ('TODOS', 2018)               |  -3.64 | 0.0003 | Prophet      | True            |
| ('TODOS', 2019)               |  -1.17 | 0.2413 | Prophet      | False           |
| ('TODOS', 2020)               |   1.25 | 0.2124 | RF recursivo | False           |
| ('TODOS', 2021)               |  -6.24 | 0      | Prophet      | True            |
| ('TODOS', 2022)               |  -5.27 | 0      | Prophet      | True            |
| ('TODOS', 2023)               |   3.26 | 0.0011 | RF recursivo | True            |
| ('TODOS', 2024)               |  -4.35 | 0      | Prophet      | True            |
| ('THEFT', 2018)               |  -6.53 | 0      | Prophet      | True            |
| ('THEFT', 2019)               |  -4.6  | 0      | Prophet      | True            |
| ('THEFT', 2020)               |   7.02 | 0      | RF recursivo | True            |
| ('THEFT', 2021)               |  12    | 0      | RF recursivo | True            |
| ('THEFT', 2022)               | -14.51 | 0      | Prophet      | True            |
| ('THEFT', 2023)               |   1.6  | 0.1097 | RF recursivo | False           |
| ('THEFT', 2024)               |  -4.72 | 0      | Prophet      | True            |
| ('BATTERY', 2018)             |  -2.58 | 0.01   | Prophet      | True            |
| ('BATTERY', 2019)             |  -2.51 | 0.0121 | Prophet      | True            |
| ('BATTERY', 2020)             |   4.78 | 0      | RF recursivo | True            |
| ('BATTERY', 2021)             |  -0.95 | 0.3439 | Prophet      | False           |
| ('BATTERY', 2022)             |   0.23 | 0.8178 | RF recursivo | False           |
| ('BATTERY', 2023)             |  -3.24 | 0.0012 | Prophet      | True            |
| ('BATTERY', 2024)             |  -1.34 | 0.1816 | Prophet      | False           |
| ('CRIMINAL DAMAGE', 2018)     |  -1.29 | 0.1957 | Prophet      | False           |
| ('CRIMINAL DAMAGE', 2019)     |  -4    | 0.0001 | Prophet      | True            |
| ('CRIMINAL DAMAGE', 2020)     |  -1.86 | 0.0635 | Prophet      | False           |
| ('CRIMINAL DAMAGE', 2021)     |  -4.05 | 0.0001 | Prophet      | True            |
| ('CRIMINAL DAMAGE', 2022)     |  -1.53 | 0.1253 | Prophet      | False           |
| ('CRIMINAL DAMAGE', 2023)     |   3.77 | 0.0002 | RF recursivo | True            |
| ('CRIMINAL DAMAGE', 2024)     |  -3.43 | 0.0006 | Prophet      | True            |
| ('ASSAULT', 2018)             |  -2.77 | 0.0056 | Prophet      | True            |
| ('ASSAULT', 2019)             |  -1.53 | 0.1249 | Prophet      | False           |
| ('ASSAULT', 2020)             |   1.43 | 0.1536 | RF recursivo | False           |
| ('ASSAULT', 2021)             |  -7.41 | 0      | Prophet      | True            |
| ('ASSAULT', 2022)             |  -1.3  | 0.1935 | Prophet      | False           |
| ('ASSAULT', 2023)             |  -9.59 | 0      | Prophet      | True            |
| ('ASSAULT', 2024)             |  -3.29 | 0.001  | Prophet      | True            |
| ('DECEPTIVE PRACTICE', 2018)  |   1.51 | 0.131  | RF recursivo | False           |
| ('DECEPTIVE PRACTICE', 2019)  |   3.36 | 0.0008 | RF recursivo | True            |
| ('DECEPTIVE PRACTICE', 2020)  |   3.5  | 0.0005 | RF recursivo | True            |
| ('DECEPTIVE PRACTICE', 2021)  |  10.92 | 0      | RF recursivo | True            |
| ('DECEPTIVE PRACTICE', 2022)  |  15.89 | 0      | RF recursivo | True            |
| ('DECEPTIVE PRACTICE', 2023)  |   5.19 | 0      | RF recursivo | True            |
| ('DECEPTIVE PRACTICE', 2024)  |   3.69 | 0.0002 | RF recursivo | True            |
| ('MOTOR VEHICLE THEFT', 2018) |  -6.61 | 0      | Prophet      | True            |
| ('MOTOR VEHICLE THEFT', 2019) |  -5.91 | 0      | Prophet      | True            |
| ('MOTOR VEHICLE THEFT', 2020) |   4.8  | 0      | RF recursivo | True            |
| ('MOTOR VEHICLE THEFT', 2021) |   4.23 | 0      | RF recursivo | True            |
| ('MOTOR VEHICLE THEFT', 2022) | -10.87 | 0      | Prophet      | True            |
| ('MOTOR VEHICLE THEFT', 2023) |   6.01 | 0      | RF recursivo | True            |
| ('MOTOR VEHICLE THEFT', 2024) |  -7.74 | 0      | Prophet      | True            |
| ('ROBBERY', 2018)             | -14.26 | 0      | Prophet      | True            |
| ('ROBBERY', 2019)             |  -2.73 | 0.0064 | Prophet      | True            |
| ('ROBBERY', 2020)             |  -1.89 | 0.0582 | Prophet      | False           |
| ('ROBBERY', 2021)             |   0.46 | 0.6473 | RF recursivo | False           |
| ('ROBBERY', 2022)             |  -0.84 | 0.4003 | Prophet      | False           |
| ('ROBBERY', 2023)             |  -4.36 | 0      | Prophet      | True            |
| ('ROBBERY', 2024)             |   4.43 | 0      | RF recursivo | True            |
| ('BURGLARY', 2018)            |   1.99 | 0.0471 | RF recursivo | True            |
| ('BURGLARY', 2019)            |  -9.36 | 0      | Prophet      | True            |
| ('BURGLARY', 2020)            |  -7.13 | 0      | Prophet      | True            |
| ('BURGLARY', 2021)            |   2.34 | 0.0195 | RF recursivo | True            |
| ('BURGLARY', 2022)            |   5.87 | 0      | RF recursivo | True            |
| ('BURGLARY', 2023)            |   2.58 | 0.0098 | RF recursivo | True            |
| ('BURGLARY', 2024)            |   5.68 | 0      | RF recursivo | True            |

### T7. Cenários do TCC (MAE, RMSE, MAPE, sMAPE)

|                                            |   MAE |   RMSE |   MAPE |   sMAPE |
|:-------------------------------------------|------:|-------:|-------:|--------:|
| ('THEFT', 2021, 'Prophet')                 | 62.88 |  71.94 |  54.45 |   81.47 |
| ('THEFT', 2021, 'RF recursivo')            | 20.34 |  26.03 |  17.91 |   19.22 |
| ('THEFT', 2021, 'RF 1 passo')              | 12.93 |  17.83 |  12.52 |   12.14 |
| ('THEFT', 2021, 'Média último ano')        | 20.17 |  25.28 |  21.26 |   19.13 |
| ('THEFT', 2021, 'Naive sazonal (t-364)')   | 28.58 |  37.59 |  30.38 |   26.12 |
| ('ASSAULT', 2018, 'Prophet')               |  6.59 |   8.44 |  12.2  |   12.07 |
| ('ASSAULT', 2018, 'RF recursivo')          |  7.18 |   9.04 |  13.37 |   13.15 |
| ('ASSAULT', 2018, 'RF 1 passo')            |  6.74 |   8.64 |  12.19 |   12.34 |
| ('ASSAULT', 2018, 'Média último ano')      |  8.72 |  10.79 |  15.81 |   15.88 |
| ('ASSAULT', 2018, 'Naive sazonal (t-364)') |  9.52 |  11.84 |  17.53 |   18.12 |
