import json
import re
from pathlib import Path

import mdf_iter
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

        def get_device_ids():
            ids = []
            for device_id in [Path(x["name"]).name for x in app.fs.listdir("/")]:
                if re.match(r"^[0-9A-F]{8}$", device_id) and app.fs.isdir(device_id):
                    ids.append(device_id)
            return ids

        def get_device_ids_names():
            ids_names = []

            # Loop all devices to get device names (meta/comment) from most recent log file
            for device_id in get_device_ids():

                # Default
                ids_names.append({"id": device_id, "name": ""})

                # Get most recent session
                sessions = [x for x in app.fs.listdir(device_id) if re.match(r'[A-F0-9]{8}/[0-9]{8}$', x["name"])]
                sessions = sorted(sessions, key=lambda x: x["name"], reverse=True)
                if len(sessions) == 0:
                    continue

                # Get most recent split
                splits = [x for x in app.fs.listdir(sessions[0]["name"]) if
                          re.match(r'[A-F0-9]{8}/[0-9]{8}/[0-9]{8}', x["name"])]
                splits = sorted(splits, key=lambda x: x["name"], reverse=True)
                if len(splits) == 0:
                    continue

                # Read meta / comment from most recent log file
                with app.fs.open(splits[0]["name"], "rb") as handle:
                    try:
                        meta_data = mdf_iter.MdfFile(handle).get_metadata()
                    except:
                        continue
                    # Update name
                    comment = meta_data.get("HDComment.Device Information.File Information.comment", {}).get(
                        "value_raw").strip()
                    ids_names[-1]["name"] = comment

            return ids_names

        if "search" in req:
            if req["search"] == "device":
                # Return list of devices
                res = get_device_ids()
            elif req["search"] == "device_name":
                # Return list of device ids and meta comments (much slower)
                res = [{"text": f"{x['id']} {x['name']}", "value": x["id"]} for x in get_device_ids_names()]
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
