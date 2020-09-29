# The same Evalscript works for Landsat-8 and Sentinel-2
# Both sensors have RGB bands named: B04, B03, B02
evalscript_landsat_true_color = evalscript_true_color

# Adjust the image size for the change in resolution
aoi_size_landsat = bbox_to_dimensions(aoi, resolution=30)