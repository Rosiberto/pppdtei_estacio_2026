from pathlib import Path
import pandas as pd


# CONFIGURAÇÃO
# --------------

arquivo_entrada = Path(
    "csv/dados_brutos/chuvas/INMET_NE_PE_A301_RECIFE_01-01-2005_A_31-12-2005.csv"
)

pasta_saida = Path(
    "csv/dados_tratados"
)

pasta_saida.mkdir(
    parents  = True,
    exist_ok = True
)


# LEITURA DO INMET
# -----------------

print("Lendo arquivo INMET...")

df = pd.read_csv(
    arquivo_entrada,
    sep      = ";",
    skiprows = 8,
    engine   = "python",
    encoding = "latin1"
)


# LIMPEZA INI
# ----------------

# remover colunas totalmente vazias
df = df.dropna(
    axis=1,
    how="all"
)

# remover espaços dos nomes
df.columns = df.columns.str.strip()


# RENOMEAR CAMPOS
# ---------------

df = df.rename(
    columns={
        "DATA (YYYY-MM-DD)": "data",
        "HORA (UTC)": "hora",
        "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)": "precipitacao_mm"
    }
)


# TRATAR PRECIPITAÇÃO
# -------------------

df["precipitacao_mm"] = pd.to_numeric(
    df["precipitacao_mm"],
    errors="coerce"
)


# Valores inválidos do INMET
df["precipitacao_mm"] = (
    df["precipitacao_mm"]
    .replace(-9999, pd.NA)
)


# Chuvas negativas não existem. remover
df.loc[
    df["precipitacao_mm"] < 0,
    "precipitacao_mm"
] = pd.NA


# substituir ausência por zero
# (importante para série de chuva)
df["precipitacao_mm"] = (
    df["precipitacao_mm"]
    .fillna(0)
)


# CRIAR DATA/HORA
# ---------------

df["data_hora"] = pd.to_datetime(
    df["data"] + " " + df["hora"],
    format="%Y-%m-%d %H:%M"
)


# CHUVA HORÁRIA
# --------------

chuva_horaria = df[
    [
        "data_hora",
        "precipitacao_mm"
    ]
]


arquivo_horaria = (
    pasta_saida /
    "chuva_horaria_recife.csv"
)


chuva_horaria.to_csv(
    arquivo_horaria,
    index=False,
    encoding="utf-8"
)


# CHUVA DIÁRIA
# -------------

chuva_diaria = (
    chuva_horaria
    .set_index("data_hora")
    .resample("D")
    ["precipitacao_mm"]
    .sum()
    .reset_index()
)


arquivo_diaria = (
    pasta_saida /
    "chuva_diaria_recife.csv"
)


chuva_diaria.to_csv(
    arquivo_diaria,
    index=False,
    encoding="utf-8"
)

# RELATÓRIO
# -----------

print("\n====================================")
print("PROCESSAMENTO FINALIZADO")
print("====================================")

print("\nDados horários:")
print(chuva_horaria.head())

print("\nDados diários:")
print(chuva_diaria.head())


print("\nResumo:")
print(chuva_diaria.describe())


print("\nArquivos gerados:")
print(arquivo_horaria)
print(arquivo_diaria)
