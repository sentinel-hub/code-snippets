from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import json
import subprocess
import argparse
import sys
import os

try:
    from osgeo import ogr, osr, gdal
except:
    sys.exit("ERROR: cannot find GDAL/OGR modules")


byoc_service_base_url = "https://services.sentinel-hub.com/byoc"


def main(client_id, client_secret, collection_id, tile_ids):
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)

    oauth.fetch_token(
        token_url="https://services.sentinel-hub.com/oauth/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    response = oauth.get(f"{byoc_service_base_url}/collections/{collection_id}")
    response.raise_for_status()
    collection = json.loads(response.text)["data"]

    bucket = collection["s3Bucket"]
    bands = iter(collection["additionalData"]["bands"])
    a_band = next(bands)

    def retrace(tile):
        s3_key = tile["path"].replace("(BAND)", a_band)
        raster = "raster.tif"
        wkt = "wkt.txt"

        command = f"gdal_translate /vsis3/{bucket}/{s3_key} {raster} -outsize 500 500"
        subprocess.run(command, shell=True, check=True)

        command = f"gdal_trace_outline {raster} -out-cs en -wkt-out {wkt}"
        subprocess.run(command, shell=True, check=True)
        os.remove(raster)

        with open(wkt) as f:
            ogr_geom = ogr.CreateGeometryFromWkt(f.read())
        os.remove(wkt)

        geojson = json.loads(ogr_geom.ExportToJson())
        geojson["crs"] = tile["tileGeometry"]["crs"]

        return geojson

    for tile_id in tile_ids:
        response = oauth.get(
            f"{byoc_service_base_url}/collections/{collection_id}/tiles/{tile_id}"
        )
        response.raise_for_status()
        tile = json.loads(response.text)["data"]

        cover_geometetry = retrace(tile)

        tile["coverGeometry"] = cover_geometetry

        response = oauth.put(
            f"{byoc_service_base_url}/collections/{collection_id}/tiles/{tile_id}",
            json=tile,
        )
        response.raise_for_status()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("client_id", help="Client id")
    parser.add_argument("client_secret", help="Client secret")
    parser.add_argument("collection_id", help="A collection id")
    parser.add_argument("tile_ids", help="A file with tile ids")
    args = parser.parse_args()

    with open(args.tile_ids) as f:
        tile_ids = f.read().splitlines()

    main(args.client_id, args.client_secret, args.collection_id, tile_ids)
