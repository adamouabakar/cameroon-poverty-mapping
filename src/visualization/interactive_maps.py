"""
Module pour créer des cartes interactives (Folium / Leafmap).
"""

import folium
import geopandas as gpd


def create_interactive_map(gdf: gpd.GeoDataFrame, column: str = "predicted_wealth"):
    """
    Crée une carte interactive simple avec Folium.
    """
    m = folium.Map(location=[3.8, 11.5], zoom_start=6)

    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=["geometry", column],
        key_on="feature.id",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Indice de richesse estimé"
    ).add_to(m)

    return m