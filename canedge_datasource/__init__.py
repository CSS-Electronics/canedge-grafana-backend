from flask import Flask, request
from flask_caching import Cache
from fsspec import AbstractFileSystem
from waitress import serve

# Flask app
app = Flask(__name__, instance_relative_config=True)

# Flask app cache
cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_THRESHOLD': 25})

def start_server(fs: AbstractFileSystem, dbs: [dict], port: int, debug: bool=False):
    """
    Start server.
    :param fs: FS mounted in CANedge "root"
    :param dbs: List of databases
    :param port: Port of the datasource server
    :param debug: Backend debug flag
    """

    # Set debug
    app.debug = debug

    # Add the shared fs and dbs to the app context
    # TODO: Not sure if this is the preferred way to share objects with the blueprints
    app.fs = fs
    app.dbs = dbs

    # Create cache for faster access on repeated calls
    cache.init_app(app)

    # Register blueprints
    from canedge_datasource.alive import alive
    app.register_blueprint(alive)

    from canedge_datasource.query import query
    app.register_blueprint(query)

    from canedge_datasource.annotations import annotations
    app.register_blueprint(annotations)

    from canedge_datasource.search import search
    app.register_blueprint(search)

    # Use waitress to serve application
    serve(app, host='0.0.0.0', port=port)


@app.before_request
def before_request():
    if app.debug:
        print(f"\nRequest: {request.method} {request.path}, {request.get_json()}")

@app.after_request
def after_request(response):
    if app.debug:
        print(f"Response: {response.status}")
    return response
