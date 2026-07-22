import geopandas as gpd
import matplotlib.pyplot  as plt

bairros = gpd.read_file("csv/dados_brutos/bairros_recife/bairros-do-recife.geojson")

#print( bairros.head() )
bairros = bairros.dropna(axis=1, how="all")
#print( bairros.info() )
#print(bairros["EBAIRRNOME"].sort_values().to_list())
bairros_m = bairros.to_crs("EPSG:31985")
bairros_m["area_m2"] = bairros_m.geometry.area
bairros_m["centroide"] = bairros_m.centroid
bairros_m["lon"] = bairros_m.centroid.x
bairros_m["lat"] = bairros_m.centroid.y
#print( bairros_m[["EBAIRRNOME", "area_m2"]].head() )
#print("Total:", len(bairros))
#print("Únicos:", bairros["EBAIRRNOME"].nunique())
#print(
#    bairros[bairros["EBAIRRNOME"].isna()]
#)
#print(bairros.geometry.geom_type.value_counts())

bairros_limpo = bairros_m[
    [
        "OBJECTID",
        "CBAIRRCODI",
        "EBAIRRNOME",
        "area_m2",
        "lon",
        "lat",
        "geometry"
    ]
].copy()

bairros_limpo = bairros_limpo.rename(
    columns={
        "OBJECTID": "id",
        "CBAIRRCODI": "codigo",
        "EBAIRRNOME": "bairro"
    }
)
'''
print(
    bairros_limpo["bairro"]
    .duplicated()
    .sum()
)
print(
    bairros_limpo["codigo"]
    .duplicated()
    .sum()
)

bairros_limpo["area_km2"] = (
    bairros_limpo["area_m2"] / 1_000_000
)

bairros_limpo.to_file(
    "csv/dados_tratados/bairros_recife.gpkg",
    layer="bairros",
    driver="GPKG"
)

bairros_limpo.drop(
    columns="geometry"
).to_csv(
    "csv/dados_tratados/bairros_recife.csv",
    index=False
)

print(
    bairros_limpo[["codigo","bairro"]]
    .sort_values("bairro")
)

bairros_limpo.info()

bairros_limpo.to_file(
    "csv/dados_tratados/bairros_recife.geojson",
    driver="GeoJSON"
)

'''

'''
bairros.plot(
    figsize=(10, 10),
    edgecolor="black"
)
plt.show()
'''