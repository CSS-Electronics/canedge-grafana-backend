import json
import mdf_iter
from flask import Blueprint, jsonify, request
from flask import current_app as app
from canedge_datasource import cache
from canedge_datasource.enums import CanedgeInterface, CanedgeChannel, SampleMethod

import logging
logger = logging.getLogger(__name__)

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

        def get_logfile_comment(log_file):
            comment = ""
            with app.fs.open(log_file, "rb") as handle:
                try:
                    meta_data = mdf_iter.MdfFile(handle, passwords=app.passwords).get_metadata()
                    comment = meta_data.get("HDcomment.File Information.comment", {}).get("value_raw").strip()
                except:
                    logger.warning("Could not extract meta data from log file")
                    pass
            return comment

        res = []

        target = req.get("target", "")
        try:
            req = json.loads(target)
        except ValueError as e:
            logger.warning(f"Search parse fail: {target}")
            raise

        if "search" in req:
            if req["search"] == "device":
                # Return list of devices
                res = list(app.fs.get_device_ids())
            elif req["search"] == "device_name":
                # Return list of device ids and meta comments (slow)
                for device in app.fs.get_device_ids():
                    # Get most recent log file
                    try:
                        log_file, _, _ = next(app.fs.get_device_log_files(device=device, reverse=True), None)
                        # Get log file comment
                        if log_file is not None:
                            comment = " " + get_logfile_comment(log_file)
                        else:
                            comment = ""
                    except:
                        print(f"Unable to list log files for {device} - review folder structure and log file names")
                        comment = ""

                    res.append({"text": f"{device}{comment}", "value": device})
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
            else:
                logger.warning(f"Unknown search: {req}")

        return jsonify(res)

    try:
        res = search_cache(request.get_json())
    except Exception as e:
        logger.warning(f"Failed to search: {e}")
        res = jsonify([])
    finally:
        return res
