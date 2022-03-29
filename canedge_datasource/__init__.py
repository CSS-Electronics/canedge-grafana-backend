import uuid
import flask
from flask import Flask, request, abort, session
from flask_caching import Cache
from fsspec import AbstractFileSystem
from waitress import serve

# Flask app
app = Flask(__name__, instance_relative_config=True)

# Flask app cache
cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_THRESHOLD": 25})

def start_server(fs: AbstractFileSystem, dbs: [dict], port: int, limit_mb: int, debug: bool=False):
    """
    Start server.
    :param fs: FS mounted in CANedge "root"
    :param dbs: List of databases
    :param port: Port of the datasource server
    :param debug: Backend debug flag
    """

    # TODO: Not sure if this is the preferred way to share objects with the blueprints

    # Set debug
    app.debug = debug

    # Init processing flag
    app.processing = False

    # Add the shared fs and dbs to the app context
    app.fs = fs
    app.dbs = dbs
    app.limit_mb = limit_mb

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
    serve(app, host='0.0.0.0', port=port, ident="canedge-grafana-backend")

@app.before_request
def before_request():

    # Limit load on /query endpoint
    if request.path == "/query":
        if app.processing is True:
            flask.abort(501)
        else:
            app.processing = True

    if app.debug:
        print(f"\nRequest: {request.method} {request.path}, {request.get_json()}")

@app.after_request
def after_request(response):

    if app.debug:
        print(f"Response: {response.status}")

    # Release query load limit
    if request.path == "/query":
        app.processing = False

    return response
