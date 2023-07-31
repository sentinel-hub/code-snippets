# download_tpdi_deliveries.py
# Downloads all raw files delivered to Sentinel Hub in an Order or Subscription


from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from pathlib import Path
from typing import Any

# Sentinel Hub
from sentinelhub import (
    SHConfig,
)


def sentinelhub_compliance_hook(response):
    response.raise_for_status()
    return response


# Configuration of the access to SentinelHub
config = SHConfig()
oauth = config.instance_id

# Your client credentials
client_id = config.sh_client_id
client_secret = config.sh_client_secret

# Create a session
client = BackendApplicationClient(client_id=client_id)
oauth = OAuth2Session(client=client)

# Get token for the session
token = oauth.fetch_token(
    token_url="https://services.sentinel-hub.com/oauth/token",
    client_secret=client_secret,
)

# All requests using this session will have an access token automatically added
resp = oauth.get("https://services.sentinel-hub.com/oauth/tokeninfo")
oauth.register_compliance_hook("access_token_response", sentinelhub_compliance_hook)

subscription_id = "<your subscription id>"
order_id ="<your order id>"


def download_file(url: str, output_path: str, overwrite: bool=False) -> None:
    """Download Third Party Data Import file
    :param url: Url pointing to a file.
    :param output_path: Local path to save the file.
    :param (optional): Overwrite a file or not.
    """
    p = Path(output_path)
    if not overwrite and p.is_file():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    response = oauth.get(url)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"Downloaded file: {output_path}")


def download_deliveries(
        request_id: str, base_url: str, deliveries: dict[str, Any], overwrite: bool=False
) -> None:
    """Download all deliveries
    :param request_id: The order id or the subscription id requested via TPDI API.
    :param base_url: Url pointing to deliveries.
    :param deliveries: Response of get subscription/order deliveries.
    :param (optional): Overwrite a file or not.
    """
    for delivery in deliveries["data"]:
        delivery_id = delivery["id"]
        files_url = base_url + f"/{delivery_id}/files"
        files_req = oauth.get(files_url)
        for file in files_req.json():
            download_file(files_url + f"/{file}", f"./{request_id}/{delivery_id}/{file}", overwrite)

def download_subscription(subscription_id: str) -> None:
    """Download a subscription
    :param subscription_id: The subscription ID
    """
    base_url = f"https://services.sentinel-hub.com/api/v1/dataimport/subscriptions/{subscription_id}/deliveries"
    response = oauth.get(base_url)
    deliveries = response.json()
    download_deliveries(base_url, deliveries)
    while 'nextToken' in deliveries['links']:
        response = oauth.get(f"{base_url}?viewtoken={deliveries['links']['nextToken']}")
        deliveries = response.json()
        download_deliveries(subscription_id, base_url, deliveries)


def download_order(order_id: str) -> None:
    """Download an order
    :param order_id: The order ID.
    """
    base_url = f"https://services.sentinel-hub.com/api/v1/dataimport/orders/{order_id}/deliveries"
    response = oauth.get(base_url)
    deliveries = response.json()
    download_deliveries(base_url, deliveries)
    while 'nextToken' in deliveries['links']:
        response = oauth.get(f"{base_url}?viewtoken={deliveries['links']['nextToken']}")
        deliveries = response.json()
        download_deliveries(order_id, base_url, deliveries)


download_subscription(subscription_id)
download_order(order_id)
