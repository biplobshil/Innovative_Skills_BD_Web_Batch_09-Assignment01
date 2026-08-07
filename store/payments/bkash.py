"""
bKash Tokenized Checkout API client.

Docs: https://developer.bka.sh/docs/tokenized-checkout-overview
Sandbox demo: https://merchantdemo.sandbox.bka.sh/tokenized-checkout/version/v2
  (use its "Checkout Only" section to validate credentials/flow by hand
  before debugging anything here — it shows raw request/response JSON)

Flow used by store/views.py:
  1. grant_token()                       -> id_token
  2. create_payment(id_token, ...)       -> {paymentID, bkashURL, ...}
     -> redirect the shopper's browser to bkashURL
  3. bKash redirects back to our callback URL with ?paymentID=...&status=...
  4. execute_payment(id_token, paymentID) -> {transactionStatus: "Completed", trxID, ...}
  5. (optional) query_payment(...) to re-verify a transaction's status later,
     e.g. from an admin action or a webhook retry.

IMPORTANT — things I could not verify without live sandbox credentials:
  - The exact JSON keys bKash returns on each call can vary slightly by
    API version. This targets v1.2.0-beta, the version referenced across
    bKash's own PDF integration guide and their reference implementations.
  - Register at https://developer.bka.sh to get a sandbox App Key, App
    Secret, Username, and Password, then set them as environment variables
    (BKASH_APP_KEY, BKASH_APP_SECRET, BKASH_USERNAME, BKASH_PASSWORD) —
    see settings.py. Nothing here will work until those are set.
  - Test wallet numbers, PIN, and OTP are provided in the sandbox docs;
    they're static test values (not secrets) meant for the sandbox only.
"""
import requests
from django.conf import settings

REQUEST_TIMEOUT = 15  # seconds


class BkashError(Exception):
    """Raised when bKash returns an error, or an unexpected response shape."""


def _api_url(path):
    return f"{settings.BKASH_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _authed_headers(id_token):
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": id_token,
        "X-App-Key": settings.BKASH_APP_KEY,
    }


def grant_token():
    """Exchange App Key/Secret + Username/Password for a short-lived id_token."""
    resp = requests.post(
        _api_url("tokenized/checkout/token/grant"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "username": settings.BKASH_USERNAME,
            "password": settings.BKASH_PASSWORD,
        },
        json={
            "app_key": settings.BKASH_APP_KEY,
            "app_secret": settings.BKASH_APP_SECRET,
        },
        timeout=REQUEST_TIMEOUT,
    )
    data = resp.json()
    if "id_token" not in data:
        raise BkashError(data.get("errorMessage") or f"Grant token failed: {data}")
    return data["id_token"]


def create_payment(id_token, amount, callback_url, merchant_invoice_number, payer_reference):
    """
    Start a payment session. Returns the full response dict — the caller
    should redirect the shopper's browser to response["bkashURL"].
    """
    resp = requests.post(
        _api_url("tokenized/checkout/create"),
        headers=_authed_headers(id_token),
        json={
            "mode": "0011",  # 0011 = checkout (tokenized), single payment
            "payerReference": payer_reference,
            "callbackURL": callback_url,
            "amount": str(amount),
            "currency": "BDT",
            "intent": "sale",
            "merchantInvoiceNumber": merchant_invoice_number,
        },
        timeout=REQUEST_TIMEOUT,
    )
    data = resp.json()
    if "paymentID" not in data or "bkashURL" not in data:
        raise BkashError(data.get("errorMessage") or f"Create payment failed: {data}")
    return data


def execute_payment(id_token, payment_id):
    """Confirm the payment after the shopper approves it on bKash's page."""
    resp = requests.post(
        _api_url("tokenized/checkout/execute"),
        headers=_authed_headers(id_token),
        json={"paymentID": payment_id},
        timeout=REQUEST_TIMEOUT,
    )
    return resp.json()


def query_payment(id_token, payment_id):
    """Check a transaction's current status — useful for reconciliation."""
    resp = requests.post(
        _api_url("tokenized/checkout/payment/status"),
        headers=_authed_headers(id_token),
        json={"paymentID": payment_id},
        timeout=REQUEST_TIMEOUT,
    )
    return resp.json()
