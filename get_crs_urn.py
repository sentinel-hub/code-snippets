#!/usr/bin/python3

import sys
import re
import json
from os import path

try:
    from osgeo import ogr, osr, gdal
except:
    sys.exit('ERROR: cannot find GDAL/OGR modules')

GEO_TIFF_CRS_PATTERN = re.compile(
    '(?:WGS 84 / (UTM|Pseudo-Mercator)(?: zone ([0-9]{1,2})([SN])))'
)


def get_crs_urn(raster_file):
    crs_tag = get_tif_crs_tag(raster_file)
    epsg_code = get_epsg_code(crs_tag)
    crs_urn = create_crs_urn(epsg_code)

    return crs_urn


def get_tif_crs_tag(raster_file):
    ds = gdal.Open(raster_file)
    prj = ds.GetProjection()
    srs = osr.SpatialReference(wkt=prj)

    return srs.GetAttrValue('projcs')


def get_epsg_code(crs_tag):
    m = GEO_TIFF_CRS_PATTERN.match(crs_tag)

    if m:
        if m.group(1) is None:
            return 4326

        if m.group(1) == 'Pseudo-Mercator':
            return 3857

        if m.group(1) == 'UTM':
            zone = int(m.group(2))
            if m.group(3) == 'N':
                return 32600 + zone
            elif m.group(3) == 'S':
                return 32700 + zone

    raise ValueError(f'No EPSG code in tag {crs_tag}')


def create_crs_urn(epsg_code):
    return f'urn:ogc:def:crs:EPSG::{epsg_code}'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Provide a path to GeoTIFF as the first argument')
        sys.exit(1)

    file = sys.argv[1]

    if not path.exists(file):
        print(f'File "{file}" does not exist')
        sys.exit(1)

    print(get_crs_urn(file))
