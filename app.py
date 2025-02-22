import json  # For loading configuration from JSON files
import logging  # For logging request and error information
from flask import Flask, request, render_template, abort, Response  # Flask framework for handling web requests
import requests  # For forwarding HTTP requests to external apps
from requests.adapters import HTTPAdapter  # Adapter for HTTP sessions
from urllib3.util.retry import Retry  # Retry strategy for handling transient errors

# Initialize Flask app
app = Flask(__name__)

# Load configuration from JSON file
with open("config.json") as f:
    config = json.load(f)

# Store app configurations in a dictionary using route as the key
apps_dict = {app_config.get("route"): app_config for app_config in config.get("apps", []) if app_config.get("route")}

# Setup HTTP session with retry strategy
session = requests.Session()
retry_strategy = Retry(
    total=3,  # Retry up to 3 times on transient errors
    backoff_factor=1,  # Wait 1 second between retries
    status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Request timeout in seconds
TIMEOUT = 10

# Configure logging to display info-level messages
logging.basicConfig(level=logging.INFO)

@app.before_request
def set_script_root():
    """Set SCRIPT_NAME in the WSGI environment based on reverse proxy headers."""
    script_name = request.headers.get('X-Forwarded-Prefix')
    if script_name:
        request.environ['SCRIPT_NAME'] = script_name

@app.route("/")
def index():
    """Render the index page with a list of available apps."""
    return render_template("index.html", apps=config.get("apps", []))

@app.route("/<app_route>/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
@app.route("/<app_route>/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
def proxy(app_route, path):
    """Proxy requests to the target app based on the route."""
    if app_route not in apps_dict:
        abort(404, description="Application not found.")

    target_app = apps_dict[app_route]
    target_url = target_app.get("url")

    if not target_url.lower().startswith("https://"):
        abort(400, description="Invalid target URL, must use HTTPS.")

    # Construct forward URL
    forward_url = f"{target_url.rstrip('/')}/{path.lstrip('/')}"
    if request.query_string:
        forward_url += "?" + request.query_string.decode("utf-8")

    # Forward request headers, excluding sensitive headers
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length", "authorization", "cookie"]}
    headers["X-Forwarded-Prefix"] = f"/{app_route}"

    try:
        logging.info(f"Forwarding {request.method} request to: {forward_url}")
        # Forward request using session
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

    # Exclude certain headers from the response
    excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
    response = Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type", "text/html"))
    for header, value in resp.headers.items():
        if header.lower() not in excluded_headers:
            response.headers[header] = value

    return response

# Run the Flask app in debug mode (development only)
if __name__ == "__main__":
    app.run(debug=True)
