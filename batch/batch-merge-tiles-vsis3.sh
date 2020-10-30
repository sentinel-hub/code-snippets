#!/bin/bash
# This helper script is intended as a tool for post-processing output tiles of your
# Sentinel Hub batch/mass processing API requests directly from your s3 bucket using
# vsis3 virtual file system for GDAL! (https://gdal.org/user/virtual_file_systems.html#vsis3-aws-s3-files)
# Without downloading all the tiles to your local machine, it merges the GeoTIFFs into a single mosaic.

# Help function that displays basic instructions on the use of the tool
print_usage() {
  echo "batch-merge-tiles-vsis3.sh"
  echo " "
  echo "Stitch together tiles from your SH Batch Processing API directly from your s3 bucket."
  echo "batch-merge-tiles-vsis3.sh [options]"
  echo " "
  echo "options:"
  echo "-h		Show brief help"
  echo "-b		AWS Bucket name"
  echo "-c		Output CRS (EPSG Code)"
  echo "-i		Interpolation method for reprojecting and creating previews. You can specify different interpolations, see https://gdal.org/programs/gdalwarp.html"
  echo "-o		Output path to folder"
  echo "-p		AWS config profile name (optional)"
  exit 0
}

# Define input flags and variable assignment
while getopts 'b:c:i:o:p:h' flag; do
  case "${flag}" in
    b) AWS_BUCKET="${OPTARG}" ;;
    c) OUTPUT_CRS="${OPTARG}" ;;
    i) INTERP="${OPTARG}" ;;
    o) OUTPUT_PATH="${OPTARG}" ;;
    p) PROFILE="${OPTARG}" ;;
    h) print_usage
       exit 1 ;;
  esac
done

# Check for bucket name
if [ -z ${AWS_BUCKET+x} ];then
  echo "Bucket name (-i) is unset";
  exit 1
fi

# Check for output path
if [ -z ${OUTPUT_PATH+x} ];then
  echo "Output path to file (-o) is unset";
  exit 1
fi

# Check for output CRS
if [ -z ${OUTPUT_CRS+x} ];then
  echo "Output CRS / EPSG code (-c,) is unset";
  exit 1
fi

# Check for interpolation method
if [ -z ${INTERP+x} ];then
  echo "Setting interpolation method to default: lanczos";
  INTERP="lanczos"
fi

echo "Preparing processing..."

# Create list with paths for object streaming from s3 with vsis3 for default or named AWS profile
if [ -z ${PROFILE} ]
then
  aws s3 ls s3://${AWS_BUCKET} --recursive | awk '{print $4}' | grep '.tif' | awk '$0="/vsis3/'${AWS_BUCKET}'/"$0' > objects_vsis3.txt
  AWS_ACCESS_KEY=$(aws configure get aws_access_key_id)
  AWS_SECRET_KEY=$(aws configure get aws_secret_access_key)
  AWS_CONFIG="--config AWS_REGION 'eu-central-1' --config AWS_ACCESS_KEY_ID "${AWS_ACCESS_KEY}" --config AWS_SECRET_ACCESS_KEY "${AWS_SECRET_KEY}
else
  aws s3 ls s3://${AWS_BUCKET} --recursive --profile $PROFILE | awk '{print $4}' | grep '.tif' | awk '$0="/vsis3/'${AWS_BUCKET}'/"$0' > objects_vsis3.txt
  AWS_ACCESS_KEY=$(aws configure get aws_access_key_id --profile $PROFILE)
  AWS_SECRET_KEY=$(aws configure get aws_secret_access_key --profile $PROFILE)
  AWS_CONFIG="--config AWS_REGION 'eu-central-1' --config AWS_ACCESS_KEY_ID "${AWS_ACCESS_KEY}" --config AWS_SECRET_ACCESS_KEY "${AWS_SECRET_KEY}
fi

# Collect CRS information of s3 objects and write them into lists named after their UTM zone
while read p; do
  filename=$(gdalsrsinfo -o proj4 $p $AWS_CONFIG | awk -F 'zone=' '{print $2}' |cut -c 1-2)
  name=$(echo ${filename} | head -c 2)
  echo $p >> ${name}_list.txt
done <objects_vsis3.txt

# Loop over object lists, create virtual rasters from them for each UTM zone and write to local raster file(s)
for file_list in ./*_list.txt
do
  zone=$(echo $file_list | awk -F '[_/]' '{print $2}')
  gdalbuildvrt $AWS_CONFIG -srcnodata 0 /vsistdout/ -input_file_list $file_list | gdalwarp $AWS_CONFIG -t_srs EPSG:$OUTPUT_CRS -r $INTERP -srcnodata 0 -dstnodata 0 /vsistdin/ $OUTPUT_PATH/$zone\_tmp_warp.tif
done

# Merge raster files
gdal_merge.py -of gtiff -co TILED=YES -co COMPRESS=LZW -co BIGTIFF=YES -n 0 -o $OUTPUT_PATH/merge.tif $OUTPUT_PATH/*tmp_warp.tif

# Translate merge (here: speeds up raster rendering in geographic information systems)
gdal_translate -co COMPRESS=LZW --config GDAL_CACHEMAX 4000 -co BIGTIFF=YES $OUTPUT_PATH/merge.tif $OUTPUT_PATH/mosaic.tif

# Create a small and a tiny scaled-down version
gdal_translate -of gtiff -co COMPRESS=LZW -co BIGTIFF=YES -r $INTERP -outsize 25% 25% $OUTPUT_PATH/mosaic.tif $OUTPUT_PATH/small.tif
gdal_translate -of gtiff -co COMPRESS=LZW -co BIGTIFF=YES -r $INTERP -outsize 25% 25% $OUTPUT_PATH/small.tif $OUTPUT_PATH/tiny.tif

# Delete temp files and lists
rm objects_vsis3.txt
rm ./*_list.txt
rm $OUTPUT_PATH/*_tmp_warp.tif
rm $OUTPUT_PATH/merge.tif

echo "Done!"
