import pandas as pd
import unidecode

def normalizar_nome(nome):
    return (
        unidecode.unidecode(str(nome))
        .upper()
        .strip()
    )

ibge = pd.read_csv(
    "csv/dados_brutos/ibge/Agregados_por_bairros_basico_BR.csv",
    sep=";",
    encoding="latin1"
)

recife = ibge[
    (ibge["NM_MUN"] == "Recife") &
    (ibge["NM_UF"] == "Pernambuco")
].copy()

recife = recife[ [
                    "NM_BAIRRO",
                    "v0001",
                    "v0002",
                    "v0003",
                    "v0004",
                    "v0005"
                  ]
                ]

#renomeio as colunas
recife = recife.rename(
    columns={
        "NM_BAIRRO":"bairro",
        "v0001":"populacao",
        "v0002":"domicilios",
        "v0005":"media_moradores"
    }
)

# criar chave
recife["bairro_key"] = (
    recife["bairro"]
    .apply(normalizar_nome)
)

# salvar
recife.to_csv(
    "csv/dados_tratados/populacao_bairros_recife.csv",
    index=False
)

print(recife.head())
print("Total bairros:", len(recife))

'''
print(
    recife[
        recife["bairro_key"].str.contains(
            "PINTOS",
            na=False
        )
    ]
)
'''