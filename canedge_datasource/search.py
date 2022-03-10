import json
import re
from pathlib import Path
from flask import Blueprint, jsonify, request
from flask import current_app as app
from canedge_datasource import cache
from canedge_datasource.enums import CanedgeInterface, CanedgeChannel, SampleMethod

search = Blueprint('search', __name__)


@search.route('/search', methods=['POST'])
def search_view():
    """
    {"search":[NAME], [OPTIONAL]}
    :return:
    """

    # Caching. Search calls are repeated each time a panel is loaded. Caching reduces communication with the backend
    @cache.memoize(timeout=50)
    def search_cache(req):

        res = []

        target = req.get("target", "")
        try:
            req = json.loads(target)
        except ValueError as e:
            print(f"Failed to search: {target}")
            return jsonify(res)

        def get_devices():
            devices = []
            for device_name in [Path(x["name"]).name for x in app.fs.listdir("/")]:
                if re.match(r"^[0-9A-F]{8}$", device_name):
                    devices.append(device_name)
            return devices

        if "search" in req:
            if req["search"] == "device":
                # Return list of devices
                res = get_devices()
            elif req["search"] == "itf":
                # Return list of interfaces
                res = [x.name for x in CanedgeInterface]
            elif req["search"] == "chn":
                # Return list channels
                res = [x.name for x in CanedgeChannel]
            elif req["search"] == "db":
                # Return list of loaded DBs
                res = list(app.dbs.keys())
            elif req["search"] == "method":
                # Return list of sampling methods
                res = [x.name for x in SampleMethod]
            elif req["search"] == "signal" and "db" in req:
                # Return list of signals in db
                db_name = req["db"].lower()
                if db_name in app.dbs.keys():
                    res = app.dbs[db_name]["signals"]

        return jsonify(res)
    return search_cache(request.get_json())
