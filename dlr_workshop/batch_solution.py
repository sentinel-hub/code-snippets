evalscript_batch = """
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
  const true_color_gain = 3.5;
  const false_color_gain = 2.5;
  return {
    "true_color": [true_color_gain * sample.B04, true_color_gain * sample.B03, true_color_gain * sample.B02],
    "false_color": [false_color_gain * sample.B08, false_color_gain * sample.B04, false_color_gain * sample.B03]
  };
}
"""
