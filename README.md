# RootRouter Project

This is a Flask-based reverse proxy application that allows users to route requests to various services.

## Features
- Proxy requests to different services.
- Handle both valid and invalid routes.
- Simulate external HTTP requests for testing.

## Installation
1. Clone the repository:
   ```bash
   git clone git@github.com:shaik/rootrouter.git
   cd rootrouter
   ```
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate# RootRouter

**RootRouter** is a Flask-based reverse proxy application that routes incoming requests to multiple Heroku apps based on URL subpaths. The project leverages an external JSON configuration file (`config.json`) to dynamically load and list available apps. It seamlessly forwards requests while preserving headers, status codes, and content types.

## Features

- **Dynamic Routing:**  
  Serve a main page at `/` listing all available apps.  
  Each app is accessible via a subpath (e.g., `/anagram`, `/emoji`, `/gibberizer`).

- **External Configuration:**  
  Store app details (name, route, Heroku URL, and description) in an external JSON file (`config.json`).

- **Secure Forwarding:**  
  Ensures that only HTTPS target URLs are used and forwards requests while preserving headers, cookies, and status codes.

- **Resilient Networking:**  
  Utilizes session pooling, retries, and timeout handling for robust external HTTP requests.

- **HTML Templating:**  
  Uses Jinja2 templates to render a dynamic, responsive main page.

- **Deployment Ready:**  
  Includes a Procfile for production deployment on Heroku and a setup script for easy project initialization.

## Project Structure


   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application
To run the application, use:
```bash
flask run
```

## Running Tests
To run the tests, use:
```bash
pytest test_app.py
```

## License
This project is licensed under the MIT License.
