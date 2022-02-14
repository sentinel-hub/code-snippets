evalscript_ndvi = """
//VERSION=3
  function setup() {
    return {
      input: [{
        bands: [
          "B04",
          "B08",
          "CLM",
          "dataMask"
        ]
      }],
      output: [
        {
          id: "NDVI",
          bands: 1
        },
        {
          id: "dataMask",
          bands: 1
        }
      ],
      mosaicking: "SIMPLE"
    };
  }

  function evaluatePixel(samples) {
      let ndvi = (samples.B08 - samples.B04) / (samples.B08 + samples.B04);

      let ndviMask = 1;
      let noCloudMask = 1;
      if (!isFinite(ndvi)) {
        ndviMask = 0;
      }
      if (samples.CLM === 1) {
        noCloudMask = 0;
      }

      return {
          NDVI: [ndvi],
          dataMask: [
            samples.dataMask * ndviMask * noCloudMask
          ]
      };
  }
  """
  