import geopandas as gpd
import pandas as pd
import unidecode


def normalizar_nome(nome):
    return (
        unidecode.unidecode(str(nome))
        .upper()
        .strip()
    )

#Carrego dados
bairros = gpd.read_file(
    "csv/dados_tratados/bairros_recife.geojson"
)

pop = pd.read_csv(
    "csv/dados_tratados/populacao_bairros_recife.csv"
)

#chave temporária
bairros["bairro_key"] = (
    bairros["bairro"]
    .apply(normalizar_nome)
)

pop["bairro_key"] = (
    pop["bairro"]
    .apply(normalizar_nome)
)

correcao = pd.read_csv(
    "csv/tabelas_auxiliares/correspondencia_bairros.csv"
)


for _, linha in correcao.iterrows():

    bairro_geo = normalizar_nome(
        linha["bairro_geo"]
    )

    bairro_ibge = normalizar_nome(
        linha["bairro_ibge"]
    )

    bairros.loc[
        bairros["bairro_key"] == bairro_geo,
        "bairro_key"
    ] = bairro_ibge

pop = pop.drop(
    columns=["bairro"]
)

#Integro
base = bairros.merge(
    pop,
    on="bairro_key",
    how="left"
)

print("Total bairros:", len(base))

print(
    base[
        [
            "bairro",
            "populacao"
        ]
    ].head()
)

print(
    "Bairros sem população:",
    base["populacao"].isna().sum()
)

print(
    base[
        base["populacao"].isna()
    ][
        [
            "bairro",
            "codigo"
        ]
    ]
)

#Salvo
base.to_file(
    "csv/dados_tratados/bairros_recife_base.geojson",
    driver="GeoJSON"
)

base.drop(
    columns="geometry"
).to_csv(
    "csv/dados_tratados/bairros_recife_base.csv",
    index=False
)


print(base.columns)