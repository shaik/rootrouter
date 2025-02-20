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
   source venv/bin/activate
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
