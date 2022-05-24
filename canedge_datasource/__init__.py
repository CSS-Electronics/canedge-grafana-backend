from flask import Flask, request, abort
from flask_caching import Cache
from fsspec import AbstractFileSystem
from waitress import serve

import logging
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__, instance_relative_config=True)

# Flask app cache
cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_THRESHOLD': 25})


def start_server(fs: AbstractFileSystem, dbs: [dict], passwords: [dict], port: int, limit_mb: int, tp_type: str):
    """
    Start server.
    :param fs: FS mounted in CANedge "root"
    :param dbs: List of databases
    :param passwords: List of log file passwords
    :param port: Port of the datasource server
    :param limit_mb: Limit amount of data to process
    :param tp_type: Type of ISO TP (multiframe) data to handle (uds, j1939, nmea)
    """

    # TODO: Not sure if this is the preferred way to share objects with the blueprints
    # Init processing flag
    app.processing = False

    # Add the shared fs and dbs to the app context
    app.fs = fs
    app.dbs = dbs
    app.passwords = passwords
    app.limit_mb = limit_mb
    app.tp_type = tp_type

    # Create cache for faster access on repeated calls
    cache.init_app(app)

    # Set simplecache logging level to WARNING to avoid heavy DEBUG level logging
    logging.getLogger('flask_caching.backends.simplecache').setLevel(logging.WARNING)

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

    logger.debug(f"Request: {request.method} {request.path}, {request.data}")

    # Limit load on /query endpoint
    if request.path == "/query":
        if app.processing is True:
            logger.info("Server busy, skipping query")
            abort(501)
        else:
            app.processing = True


@app.after_request
def after_request(response):

    logger.debug(f"Response: {response.status}")

    # Release query load limit
    if request.path == "/query":
        app.processing = False

    return response
