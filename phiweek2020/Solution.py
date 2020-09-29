evalscript_false_color = """
//VERSION=3

function setup() {
  return {
    input: ["B08", "B04", "B03"],
    output: { bands: 3 }
  };
}

function evaluatePixel(sample) {
  let gain = 2.5;
  return [gain * sample.B08, gain * sample.B04, gain * sample.B03];
}
"""