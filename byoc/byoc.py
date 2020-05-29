#!/usr/bin/env python
import time
import re
import os
import logging
import argparse
import sys
import json

from oauthlib.oauth2 import BackendApplicationClient, TokenExpiredError
from requests import ConnectionError
from requests_oauthlib import OAuth2Session


logging.basicConfig(format="%(message)s")
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


TOKEN_URL = "https://services.sentinel-hub.com/oauth/token"
CATALOG_URL = "https://services.sentinel-hub.com/api/v1/byoc/global"

AWS_EU_CENTRAL_1 = "aws-eu-central-1"
AWS_US_WEST_2 = "aws-us-west-2"
MUNDI = "mundi"

LOCATION_ENDPOINTS = {
    AWS_EU_CENTRAL_1: "https://services.sentinel-hub.com/api/v1/byoc",
    AWS_US_WEST_2: "https://services-uswest2.sentinel-hub.com/api/v1/byoc",
    MUNDI: "https://shservices.mundiwebservices.com/api/v1/byoc",
}


def get_endpoint(location):
    return LOCATION_ENDPOINTS[location]


class ByocClient:

    location_cache = dict()

    def __init__(self, client_id=None, client_secret=None):
        client_id = client_id if client_id is not None else os.environ["SH_CLIENT_ID"]

        if client_id is None:
            raise Error("client id missing")

        client_secret = (
            client_secret
            if client_secret is not None
            else os.environ["SH_CLIENT_SECRET"]
        )

        if client_secret is None:
            raise Error("client secret missing")

        client_args = {"client_id": client_id}
        shub_dir = os.path.join(os.path.expanduser("~"), ".sentinelhub")
        token_file = os.path.join(shub_dir, f"{client_id}.json")

        cached_token = None
        if not os.path.exists(shub_dir):
            os.mkdir(shub_dir)
        elif os.path.exists(token_file):
            with open(token_file) as fhandle:
                cached_token = json.load(fhandle)

        self.oauth = OAuth2Session(
            client=BackendApplicationClient(client_id=client_id, token=cached_token)
        )

        token = self.oauth.fetch_token(
            token_url=TOKEN_URL, client_id=client_id, client_secret=client_secret
        )

        if (
            cached_token is None
            or token["access_token"] != cached_token["access_token"]
        ):
            with open(token_file, "w") as fhandle:
                json.dump(token, fhandle)

    def get_collections(self):
        resp = self.oauth.get(CATALOG_URL)
        resp.raise_for_status()
        return resp.json()["data"]

    def create_collection(self, location, collection):
        endpoint = get_endpoint(location)
        resp = self.oauth.post(f"{endpoint}/collections", json=collection)
        resp.raise_for_status()
        return resp.json()["data"]

    def create_tile(self, collection_id, tile):
        collection_url = self.get_collection_url(collection_id)
        resp = self.oauth.post(f"{collection_url}/tiles", json=tile)
        resp.raise_for_status()
        return resp.json()["data"]

    def get_collection(self, collection_id):
        collection_url = self.get_collection_url(collection_id)
        resp = self.oauth.get(collection_url)
        resp.raise_for_status()
        return resp.json()["data"]

    def get_tiles(self, collection_id):
        collection_url = self.get_collection_url(collection_id)
        fetch_url = f"{collection_url}/tiles"

        while fetch_url is not None:
            resp = self.oauth.get(fetch_url)
            resp.raise_for_status()
            json = resp.json()

            tiles = json["data"]
            links = json["links"]
            fetch_url = links.get("next")

            for tile in tiles:
                yield tile

            time.sleep(0.1)

    def delete_collection(self, collection_id):
        collection_url = self.get_collection_url(collection_id)
        resp = self.oauth.delete(collection_url)
        resp.raise_for_status()

    def delete_tile(self, collection_id, tile_id):
        collection_url = self.get_collection_url(collection_id)
        resp = self.oauth.delete(f"{collection_url}/tiles/{tile_id}")
        resp.raise_for_status()

    def get_collection_url(self, collection_id):
        location = self.get_location(collection_id)
        endpoint = get_endpoint(location)
        return f"{endpoint}/collections/{collection_id}"

    def get_location(self, collection_id):
        if collection_id not in self.location_cache:
            resp = self.oauth.get(f"{CATALOG_URL}/{collection_id}")
            resp.raise_for_status()
            location = resp.json()["data"]["location"]
            self.location_cache[collection_id] = location

        return self.location_cache[collection_id]


class ByocCli:
    def __init__(self):
        commands = {
            "get-collections": self.get_collections,
            "create-collection": self.create_collection,
            "create-tile": self.create_tile,
            "get-collection": self.get_collection,
            "get-tiles": self.get_tiles,
            "delete-collection": self.delete_collection,
            "delete-tile": self.delete_tile,
        }

        parser = argparse.ArgumentParser(
            prog="byoc",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:

  To get collections:

    byoc get-collections | jq '{id, name, location, s3Bucket}

  To get collection tiles:

    byoc get-tiles <collection id> | jq '{id, status, additionalData}'

  To get ingested tiles one per row:

    byoc get-tiles <collection id> | jq 'select(.status == "INGESTED") | "\(.path)"'

  To get failed tiles with causes:

    byoc get-tiles <collection id> | jq 'select(.status == "FAILED") | "\(.path) \(.additionalData.failedIngestionCause)"' 

  To get number of tiles by status:

    byoc get-tiles <collection id> | jq 'group_by(.status) | map({ status: .[0].status, length: length })'

  To delete failed tiles:

    byoc get-tiles <collection id> | jq 'select(.status == "FAILED") | "\(.id)"' | xargs -I {} byoc delete-tile <collection id> {}
        """,
        )
        parser.add_argument("command", choices=commands.keys())
        args = parser.parse_args(sys.argv[1:2])

        self.command = commands[args.command]

    def run(self):
        self.command()

    @staticmethod
    def get_collections():
        collections = ByocClient().get_collections()

        for c in collections:
            print(json.dumps(c))

    @staticmethod
    def create_collection():
        parser = argparse.ArgumentParser()
        parser.add_argument("location")
        parser.add_argument("name")
        parser.add_argument("bucket")
        args = parser.parse_args(sys.argv[2:])

        collection = {"name": args.name, "s3Bucket": args.bucket}
        collection = ByocClient().create_collection(args.location, collection)

        print(json.dumps(collection))

    @staticmethod
    def create_tile():
        parser = argparse.ArgumentParser()
        parser.add_argument("collection_id")
        parser.add_argument("path")
        parser.add_argument("--time")
        args = parser.parse_args(sys.argv[2:])

        tile = {"path": args.path, "sensingTime": args.time}
        tile = ByocClient().create_tile(args.collection_id, tile)

        print(json.dumps(tile))

    @staticmethod
    def get_collection():
        parser = argparse.ArgumentParser()
        parser.add_argument("collection_id")
        args = parser.parse_args(sys.argv[2:])

        collection = ByocClient().get_collection(args.collection_id)

        print(json.dumps(collection))

    @staticmethod
    def get_tiles():
        parser = argparse.ArgumentParser()
        parser.add_argument("collection_id")
        args = parser.parse_args(sys.argv[2:])

        tiles = ByocClient().get_tiles(args.collection_id)

        for tile in tiles:
            print(json.dumps(tile))

    @staticmethod
    def delete_collection():
        parser = argparse.ArgumentParser()
        parser.add_argument("collection_id")
        args = parser.parse_args(sys.argv[2:])

        ByocClient().delete_collection(args.collection_id)

    @staticmethod
    def delete_tile():
        parser = argparse.ArgumentParser()
        parser.add_argument("collection_id")
        parser.add_argument("tile_id")
        args = parser.parse_args(sys.argv[2:])

        ByocClient().delete_tile(args.collection_id, args.tile_id)


if __name__ == "__main__":
    ByocCli().run()
