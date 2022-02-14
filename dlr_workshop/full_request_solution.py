# Read geometry
field_2_crs = other_degraded_areas.crs.to_epsg()
field_2_geom = Geometry(other_degraded_areas.geometry.iloc[1], crs=field_2_crs)

# Create evalscript
evalscript_field_2 = """
//VERSION=3

function setup() {
  return {
    input: ["B02", "B03", "B04", "B08"],
    output: [
      {
        "id": "true_color",
        "bands": 3
      },
      {
        "id": "false_color",
        "bands": 3
      }
    ]
  };
}

function evaluatePixel(sample) {
  const true_color_gain = 5;
  const false_color_gain = 2.5;
  return {
    "true_color": [true_color_gain * sample.B04, true_color_gain * sample.B03, true_color_gain * sample.B02],
    "false_color": [false_color_gain * sample.B08, false_color_gain * sample.B04, false_color_gain * sample.B03]
  };
}
"""

# Create requests
field_2_before_drop_request = SentinelHubRequest(
    evalscript=evalscript_field_2,
    input_data=[
        SentinelHubRequest.input_data(
            data_collection=DataCollection.SENTINEL2_L2A,
            time_interval=("2019-05-20", "2019-05-31"),
            mosaicking_order="leastRecent"
        )
    ],
    responses=[
        SentinelHubRequest.output_response('true_color', MimeType.TIFF),
        SentinelHubRequest.output_response('false_color', MimeType.TIFF)
    ],
    geometry=field_2_geom,
    resolution=(10, 10),
    # This time we don't specify size parameter
    config=config
)

field_2_after_drop_request = SentinelHubRequest(
    evalscript=evalscript_field_2,
    input_data=[
        SentinelHubRequest.input_data(
            data_collection=DataCollection.SENTINEL2_L2A,
            time_interval=("2019-07-21", "2019-07-31"),
            mosaicking_order="mostRecent"
        )
    ],
    responses=[
        SentinelHubRequest.output_response('true_color', MimeType.TIFF),
        SentinelHubRequest.output_response('false_color', MimeType.TIFF)
    ],
    geometry=field_2_geom,
    resolution=(10, 10),
    # This time we don't specify size parameter
    config=config
)

# Get data
field_2_before_drop_tc = field_2_before_drop_request.get_data()[0]['true_color.tif']
field_2_before_drop_fc = field_2_before_drop_request.get_data()[0]['false_color.tif']
field_2_after_drop_tc = field_2_after_drop_request.get_data()[0]['true_color.tif']
field_2_after_drop_fc = field_2_after_drop_request.get_data()[0]['false_color.tif']