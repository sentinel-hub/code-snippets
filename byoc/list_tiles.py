from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import json
import argparse


byoc_service_base_url = "https://services.sentinel-hub.com/byoc"


def main(client_id, client_secret, collection_id):
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)

    token = oauth.fetch_token(
        token_url="https://services.sentinel-hub.com/oauth/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    def get_paginated_tiles(url):
        response = oauth.get(url)
        response.raise_for_status()
        paginated_tiles = json.loads(response.text)
        return paginated_tiles["data"], paginated_tiles["links"].get("next")

    def get_tile_iterator(collection_id):
        url = f"{byoc_service_base_url}/collections/{collection_id}/tiles"

        while url is not None:
            tiles, url = get_paginated_tiles(url)
            for tile in tiles:
                yield tile

    tiles = get_tile_iterator(collection_id)
    
    for tile in tiles:
        if tile["status"] != "INGESTED":
            continue

        print(tile['id'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("client_id", help="An oauth client id")
    parser.add_argument("client_secret", help="An oauth client secret")
    parser.add_argument("collection_id", help="A collection id")
    args = parser.parse_args()

    main(args.client_id, args.client_secret, args.collection_id)
