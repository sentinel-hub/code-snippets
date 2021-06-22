#!/bin/bash
# This is a helper scripts that merges a bunch of GeoTIFFs into a single large one."
# It is intended as a tool for post-processing output tiles of your
# Sentinel Hub batch/mass processing API requests.
# Requires bash shell with a working GDAL installation.

if [ "$#" -ne 1 ]; then
  echo "You must provide input directory. Also, don't forget to set the output CRS in the script."
  exit 1
fi

INPUT_DIR=$1 #this directory and all its subdirectories will be searched for .tif files

INTERP="lanczos"

OUTPUT_CRS=32753 #select output CRS, for example the UTM zone of the center of your area of interest
OUTPUT_DIR="output"
mkdir -p $OUTPUT_DIR

#collect all input files and group them into directories named after their CRS
for T in $(find $INPUT_DIR -name '*.tif'); do
  CRS=$(gdalsrsinfo $T -o epsg |grep -i 'epsg:' | sed 's/.*\://')
  CRS_DIR=$OUTPUT_DIR/$CRS.crs
  mkdir -p $CRS_DIR
  cp $T $CRS_DIR/$(echo $T | tr '/' '_')
  #for a faster, scaled-down preview, replace the cp above with:
  #gdal_translate -of gtiff -co COMPRESS=LZW -r $INTERP -outsize 25% 25% $T $CRS_DIR/$(echo $T | tr '/' '_')
done

pushd $OUTPUT_DIR >/dev/null

#for each CRS, merge all tiles and reproject them to OUTPUT_CRS
for CRS in *.crs; do
  pushd $CRS >/dev/null

  OUT="../$CRS"
  gdal_merge.py -of gtiff -co TILED=YES -co COMPRESS=LZW -n 0 -o "$OUT.tif" *
  gdalwarp -t_srs EPSG:$OUTPUT_CRS -r $INTERP -co COMPRESS=LZW -srcnodata 0 -dstnodata 0 -multi "$OUT.tif" "$OUT-to-$OUTPUT_CRS.tif"

  popd >/dev/null
  rm -rf $CRS #delete the intermediate files for this CRS
done

#merge all reprojected images into full.tif
#gdal_merge may overflow the memory and gdalwarp may fail on huge files with compressed output,
#so we use gdalbuildvrt | gdal_translate instead
gdalbuildvrt -srcnodata 0 /vsistdout/ *-to-$OUTPUT_CRS.tif | gdal_translate -r $INTERP -co COMPRESS=LZW --config GDAL_CACHEMAX 4000 /vsistdin/ full.tif

#delete intermediate files
rm -f *.crs.tif
rm -f *.crs-to-*.tif

#create a small and a tiny scaled-down version
gdal_translate -of gtiff -co COMPRESS=LZW -r $INTERP -outsize 25% 25% full.tif small.tif
gdal_translate -of gtiff -co COMPRESS=LZW -r $INTERP -outsize 25% 25% small.tif tiny.tif

#optionally, create brigter versions of all output sizes
#for SIZE in "full" "small" "tiny"; do
#  gdal_calc.py -A $SIZE.tif --allBands=A --outfile="$SIZE"_bright.tif --calc="A*2.0" --NoDataValue=0 --co="COMPRESS=LZW"
#done

popd >/dev/null
