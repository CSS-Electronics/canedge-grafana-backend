import json
import canedge_browser
import mdf_iter
from flask import Blueprint, jsonify, request
from flask import current_app as app
from canedge_datasource import cache
from canedge_datasource.time_range import parse_time_range

import logging
logger = logging.getLogger(__name__)

annotations = Blueprint('annotations', __name__)


@annotations.route('/annotations', methods=['POST'])
def annotations_view():
    """
    {"annotation":[NAME], [OPTIONAL]}

    Examples:
        {"annotation":"session", "device":"AABBCCDD"}
        {"annotation":"split", "device":"AABBCCDD"}
    """

    # Caching
    @cache.memoize(timeout=50)
    def annotations_cache(req):

        res = []

        query_req = req["annotation"].get("query", "")
        try:
            annotation_req = json.loads(query_req)
        except ValueError as e:
            logger.warning(f"Annotation parse fail: {query_req}")
            raise

        if "annotation" not in annotation_req:
            logger.warning(f"Unknown annotation request: {query_req}")
            raise ValueError

        if annotation_req["annotation"] not in ["session", "split"]:
            logger.warning(f"Unknown annotation request: {annotation_req['annotation']}")
            raise ValueError

        if "device" not in annotation_req:
            logger.warning("Unknown annotation device")
            raise ValueError

        # Get time interval to annotate
        start_date, stop_date = parse_time_range(req["range"]["from"], req["range"]["to"])

        # Get log files in time interval

        log_files = canedge_browser.get_log_files(app.fs, annotation_req["device"], start_date=start_date,
                                                  stop_date=stop_date, passwords=app.passwords)

        for log_file in log_files:

            # Parse log file path
            device_id, session_no, split_no, ext = app.fs.path_to_pars(log_file)

            if None in [device_id, session_no, split_no, ext]:
                continue

            # Only generate annotation if annotation is split or annotation is session with first split file
            if not ((annotation_req["annotation"] == "split") or
                    (annotation_req["annotation"] == "session" and int(split_no, 10) == 1)):
                continue

            # Get file start time
            with app.fs.open(log_file, "rb") as handle:
                mdf_file = mdf_iter.MdfFile(handle, passwords=app.passwords)
                log_file_start_timestamp_ns = mdf_file.get_first_measurement()

            res.append({
                "text": f"{log_file}\n"
                        f"Session: {int(session_no, 10)}\n"
                        f"Split: {int(split_no, 10)}\n"
                        f"Size: {app.fs.size(log_file) >> 20} MB",
                "time": log_file_start_timestamp_ns / 1000000,
            })

        return jsonify(res)

    try:
        res = annotations_cache(request.get_json())
    except Exception as e:
        logger.warning(f"Failed to annotate: {e}")
        res = jsonify([])
    finally:
        return res
