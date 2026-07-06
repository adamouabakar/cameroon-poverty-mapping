"""
Fonctions pour exporter les résultats depuis Google Earth Engine.
"""

import ee


def export_image_to_drive(image, description, folder, region, scale=1000):
    """Exporte une image GEE vers Google Drive."""
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        region=region,
        scale=scale,
        fileFormat='GeoTIFF'
    )
    task.start()
    return task