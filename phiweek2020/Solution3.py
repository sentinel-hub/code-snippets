evalscript_landsat_true_color_improved = """
//VERSION=3
function setup() {
  return {
    input: ["B02","B03", "B04", "B08"],
    output: { bands: 3 }
  };
}

function evaluatePixel(samples) {
  
  // Use weighted arithmetic average for pan-sharpening
  let s2PanR3 = (samples.B04 + samples.B03 + samples.B02) / 3
  let s2ratioWR3 = s2PanR3 / samples.B08
  let gain = 2.5
  return [gain * samples.B04 * s2ratioWR3, gain * samples.B03 * s2ratioWR3, gain * samples.B02 * s2ratioWR3]
}
"""

# Adjust the image size for the change in resolution
aoi_size_landsat = bbox_to_dimensions(aoi, resolution=15)