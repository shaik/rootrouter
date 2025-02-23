import json
import logging
from flask import Flask, request, render_template, abort, Response
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)
app.url_map.strict_slashes = False

# Load config for apps
with open("config.json") as f:
    config = json.load(f)

apps_dict = {c["route"]: c for c in config.get("apps", []) if "route" in c}

# Setup session with retries
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET","HEAD","OPTIONS","POST","PUT","DELETE","PATCH"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

TIMEOUT = 10
logging.basicConfig(level=logging.INFO)

@app.route("/")
def index():
    """Show main page with links."""
    return render_template("index.html", apps=config.get("apps", []))

@app.route("/<app_route>", defaults={"path": ""}, methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"])
@app.route("/<app_route>/<path:path>", methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"])
def proxy(app_route, path):
    """Proxy to the specified sub-app route."""
    if app_route not in apps_dict:
        abort(404, description="No such app route configured.")

    target_url = apps_dict[app_route].get("url")
    if not target_url or not target_url.lower().startswith("https://"):
        abort(400, description="App must have a valid HTTPS URL.")

    # Build the forward URL
    forward_url = f"{target_url.rstrip('/')}/{path.lstrip('/')}"
    if request.query_string:
        forward_url += "?" + request.query_string.decode("utf-8")

    # Filter out sensitive headers
    forward_headers = {
        k: v
        for k,v in request.headers.items()
        if k.lower() not in ("host","content-length","authorization","cookie")
    }
    # This is crucial: sub-app uses X-Script-Name to prefix its routes
    forward_headers["X-Script-Name"] = f"/{app_route}"

    logging.info(f"Proxying {request.method} {request.path} => {forward_url}")

    # Forward request
    try:
        resp = session.request(
            method=request.method,
            url=forward_url,
            headers=forward_headers,
            data=request.get_data() if request.method in ["POST","PUT","PATCH"] else None,
            allow_redirects=False,
            timeout=TIMEOUT,
            stream=True
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed request to {forward_url}: {e}")
        abort(502, description="Bad Gateway: " + str(e))

    # Build a Flask response
    excluded = ["content-encoding","content-length","transfer-encoding","connection"]
    flask_resp = Response(resp.content, status=resp.status_code)
    for h,v in resp.headers.items():
        if h.lower() not in excluded:
            flask_resp.headers[h] = v

    return flask_resp

# In your root router app.py

import re
from flask import Flask, request, Response, abort
import requests
import logging

# Suppose you already have: app = Flask(__name__), a config, apps_dict, etc.

@app.route("/static/<path:filename>")
def brute_force_static(filename):
    """
    Brute-force approach to serve static files by analyzing the Referer
    to guess which sub-app's static directory to use.
    """
    referer = request.headers.get("Referer", "")
    referer_lower = referer.lower()

    # 1. Guess the route from the referer
    #   For example, if you have 'emoji', 'gibberizer', 'anagram' sub-apps:
    if "/emoji" in referer_lower:
        route = "emoji"
    elif "/gibberizer" in referer_lower:
        route = "gibberizer"
    elif "/anagram" in referer_lower:
        route = "anagram"
    else:
        # Fallback if we can't guess -> pick a default or 404
        logging.warning(f"Unable to determine route from Referer: {referer}")
        abort(404, description="No route found for static request")

    # 2. Build the forward URL to sub-app's /static/filename
    if route not in apps_dict:
        abort(404, description="Route not found in config")

    target_url = apps_dict[route]["url"]
    forward_url = f"{target_url.rstrip('/')}/static/{filename}"

    logging.info(f"Brute-forcing static request for /static/{filename} => {forward_url}")

    # 3. Proxy this file request
    try:
        resp = requests.get(forward_url, timeout=10, stream=True)
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to {forward_url} failed: {e}")
        abort(502, description="Bad Gateway: " + str(e))

    if resp.status_code == 404:
        # File not found in the sub-app's static directory
        abort(404, description="Static file not found")

    # 4. Build a Flask response
    excluded = ["content-encoding", "content-length", "transfer-encoding", "connection"]
    flask_resp = Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))
    for h, v in resp.headers.items():
        if h.lower() not in excluded:
            flask_resp.headers[h] = v

    return flask_resp

if __name__ == "__main__":
    app.run(debug=True)
