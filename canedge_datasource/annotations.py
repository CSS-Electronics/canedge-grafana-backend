import json
import re
import canedge_browser
import mdf_iter
from flask import Blueprint, jsonify, request
from flask import current_app as app
from canedge_datasource import cache
from canedge_datasource.time_range import parse_time_range

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
            print(f"Failed parse annotation: {query_req}")
            return jsonify(res)

        if "annotation" not in annotation_req:
            print(f"Unknown annotation {query_req}")

        # Split / session annotations
        elif annotation_req["annotation"] in ["session", "split"] and "device" in annotation_req:

            # Get time interval to annotate
            start_date, stop_date = parse_time_range(req["range"]["from"], req["range"]["to"])

            # Get log files in time interval
            log_files = canedge_browser.get_log_files(app.fs, annotation_req["device"], start_date=start_date,
                                                      stop_date=stop_date)

            for log_file in log_files:

                # Parse filename
                file_matches = re.match(
                    r"\S?[0-9A-F]{8}/(?P<session_no>\d{8})/(?P<split_no>\d{8})(?:-[0-9A-F]{8}){0,1}\.MF4$",
                    log_file,
                    re.IGNORECASE)

                if not file_matches:
                    continue

                session_no = file_matches.group("session_no")
                split_no = file_matches.group("split_no")

                # Only generate annotation if annotation is split or annotation is session with first split file
                if not ((annotation_req["annotation"] == "split") or
                        (annotation_req["annotation"] == "session" and int(split_no, 10) == 1)):
                    continue

                # Get file start time
                with app.fs.open(log_file, "rb") as handle:
                    mdf_file = mdf_iter.MdfFile(handle)
                    log_file_start_timestamp_ns = mdf_file.get_first_measurement()

                res.append({
                    "text": f"{log_file}\n"
                            f"Session: {int(session_no, 10)}\n"
                            f"Split: {int(split_no, 10)}\n"
                            f"Size: {app.fs.size(log_file) >> 20} MB",
                    "time": log_file_start_timestamp_ns / 1000000,
                })

        return jsonify(res)

    return annotations_cache(request.get_json())
