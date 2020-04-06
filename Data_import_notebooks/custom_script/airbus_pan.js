//VERSION=3
function setup() {
  return {
    input: ["B0", "B1", "B2", "PAN"],
    output: { bands: 3 }
  };
}
let minVal = 0.0;
let maxVal = 3000;
let viz = new DefaultVisualizer(minVal, maxVal);
function evaluatePixel(samples) {
  let sudoPanW = (samples.B1 + samples.B2 + samples.B0) / 3;
  let ratioW = samples.PAN / sudoPanW;
  let val = [samples.B2 * ratioW, samples.B1 * ratioW, samples.B0 * ratioW];
  return viz.processList(val);
}
