def create_cluster_buffers(
    gdf: gpd.GeoDataFrame,
    urban_buffer_km: float = 2.0,
    rural_buffer_km: float = 5.0
) -> gpd.GeoDataFrame:
    """
    Crée des buffers autour des grappes en gérant correctement le système de coordonnées.
    """
    gdf = gdf.copy()

    # Définir les buffers selon urbain/rural
    gdf["buffer_km"] = gdf["urban_rural"].map({
        "urban": urban_buffer_km,
        "rural": rural_buffer_km
    }).fillna(rural_buffer_km)

    # Reprojeter en mètres (UTM zone 33N - adapté au Cameroun)
    gdf_projected = gdf.to_crs(epsg=32633)

    # Créer le buffer en mètres
    gdf_projected["geometry"] = gdf_projected.geometry.buffer(
        gdf_projected["buffer_km"] * 1000
    )

    # Reprojeter en WGS84 (latitude/longitude) pour la suite
    gdf_final = gdf_projected.to_crs(epsg=4326)

    return gdf_final