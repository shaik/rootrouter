import json
import logging
from flask import Flask, request, render_template, abort, Response
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

# Load configuration
with open("config.json") as f:
    config = json.load(f)

apps_dict = {app_config.get("route"): app_config for app_config in config.get("apps", []) if app_config.get("route")}

# HTTP session with retry strategy
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

TIMEOUT = 10

# Setup logging
logging.basicConfig(level=logging.INFO)

@app.route("/")
def index():
    return render_template("index.html", apps=config.get("apps", []))

@app.route("/<app_route>/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
@app.route("/<app_route>/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
def proxy(app_route, path):
    if app_route not in apps_dict:
        abort(404, description="Application not found.")

    target_app = apps_dict[app_route]
    target_url = target_app.get("url")

    if not target_url.lower().startswith("https://"):
        abort(400, description="Invalid target URL, must use HTTPS.")

    forward_url = f"{target_url.rstrip('/')}/{path.lstrip('/')}"
    if request.query_string:
        forward_url += "?" + request.query_string.decode("utf-8")

    headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length", "authorization", "cookie"]}

    try:
        logging.info(f"Forwarding {request.method} request to: {forward_url}")
        resp = session.request(
            method=request.method,
            url=forward_url,
            headers=headers,
            data=request.get_data() if request.method in ["POST", "PUT", "PATCH"] else None,
            allow_redirects=False,
            timeout=TIMEOUT,
            stream=True
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to {forward_url} failed: {e}")
        abort(502, description="Bad Gateway: " + str(e))

    excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
    response = Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type", "text/html"))
    for header, value in resp.headers.items():
        if header.lower() not in excluded_headers:
            response.headers[header] = value

    return response

if __name__ == "__main__":
    app.run(debug=True)
