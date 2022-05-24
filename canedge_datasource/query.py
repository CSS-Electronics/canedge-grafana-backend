import json
from datetime import datetime
from enum import IntEnum, auto
from flask import Blueprint, jsonify, request
from flask import current_app as app
from canedge_datasource import cache
from canedge_datasource.enums import CanedgeInterface, CanedgeChannel, SampleMethod
from canedge_datasource.signal import SignalQuery, time_series_phy_data, table_raw_data, table_fs
from canedge_datasource.time_range import parse_time_range

import logging
logger = logging.getLogger(__name__)

query = Blueprint('query', __name__)


class RequestType(IntEnum):
    """
    Defines what the user is requesting.
    """
    DATA = auto()
    INFO = auto()


def _json_target_decode(dct):
    """Target json object decoder"""
    if "itf" in dct:
        dct["itf"] = CanedgeInterface[dct["itf"].upper()]
    if "chn" in dct:
        dct["chn"] = CanedgeChannel[dct["chn"].upper()]
    if "db" in dct:
        dct["db"] = dct["db"].lower()
    if "method" in dct:
        dct["method"] = SampleMethod[dct["method"].upper()]
    if "signal" in dct:
        # Grafana json plugin uses (X|Y|Z) to delimit multiple selections. Split to array
        dct["signal"] = dct["signal"].replace("(", "").replace(")", "").split("|")
    if "type" in dct:
        dct["type"] = RequestType[dct["type"].upper()]
    return dct

def _json_decode_target(target):
    # Decode target (the query entered by the user formatted as json)
    try:
        return json.loads(target, object_hook=_json_target_decode)
    except KeyError as e:
        # Handle invalid enum mapping errors (key not exist)
        logger.warning(f"Invalid target {e}")
        return None
    except Exception as e:
        raise

@query.route('/query', methods=['POST'])
def query_view():
    """
    {"query":[NAME], [OPTIONAL]}

    The user query is stored in the "target" field.

    Table request example:
    {
      "panelId":1,
      "range": {
        "from": "2020-10-28T14:33:57.732Z",
        "to": "2020-10-28T15:01:25.048Z"
      },
      "intervalMs": 5000,
      "targets": [
        {
          "target": "...",
          "type": "table"
        }
      ],
      "maxDataPoints": 421
    }

    Time-series request example:
    {
      "panelId":1,
      "range": {
        "from": "2020-10-28T14:33:57.732Z",
        "to": "2020-10-28T15:01:25.048Z"
      },
      "intervalMs": 2000,
      "targets": [
        {
          "target": "...",
          "type": "timeserie"
        }
      ],
      "maxDataPoints": 831
    }

    The result of multiselect variables is formatted as e.g. "(AccelerationX|AccelerationY|AccelerationZ)"

    If one panel contains several queries, then these each becomes an element in "targets". Separate panels generate
    separate independent http requests - each with a unique "panelId".

    """

    # Caching on a request level. Drastically improves performance when the same panel is loaded twice - e.g. when
    # annotations are enabled/disabled without changing the view.
    @cache.memoize(timeout=50)
    def query_cache(req):

        res = []

        # Get query time interval
        start_date, stop_date = parse_time_range(req["range"]["from"], req["range"]["to"])

        # Get panel type (targets with mixed types not supported)
        panel_types = [x.get("type", "timeseries") for x in req["targets"]]

        if all(x == panel_types[0] for x in panel_types):

            if panel_types[0] in ["timeseries", "timeserie"]:
                res = _query_time_series(req, start_date, stop_date)
            elif panel_types[0] in ["table"]:
                res = _query_table(req, start_date, stop_date)

        return res

    # Get request
    req_in = request.get_json()

    # Drop unused and changing keys to improve caching (only works on identical requests)
    req_in.pop('requestId', None)
    req_in.pop('startTime', None)

    return jsonify(query_cache(req_in))


def _query_time_series(req: dict, start_date: datetime, stop_date: datetime) -> list:

    # Loop all requested targets
    signal_queries = []
    for elm in req["targets"]:

        # Decode target
        target_req = _json_decode_target(elm["target"])
        if target_req is None:
            logger.warning(f"Failed to query target: {elm['target']}")
            continue

        # Fields required for series
        if not all(x in target_req for x in ["device", "itf", "chn", "db", "signal"]):
            logger.warning(f"Target missing required fields: {target_req}")
            continue

        # Check that DB is known
        if target_req["db"] not in app.dbs.keys():
            logger.warning(f"Unknown DB: {target_req['db']}")
            continue

        # If multiple signals in request, add each as signal query
        for signal in target_req["signal"]:
            # Provide a readable unique target name (the list of signals is replaced by the specific signal)
            target_name = ":".join([str(x) for x in dict(target_req, signal=signal).values()])

            signal_queries.append(SignalQuery(refid=elm["refId"],
                                              target=target_name,
                                              device=target_req["device"],
                                              itf=target_req["itf"],
                                              chn=target_req["chn"],
                                              db=app.dbs[target_req["db"]]["db"],
                                              signal_name=signal,
                                              interval_ms=int(req["intervalMs"]),
                                              method=target_req.get("method", SampleMethod.NEAREST)))

    # Get signals
    return time_series_phy_data(fs=app.fs,
                                signal_queries=signal_queries,
                                start_date=start_date,
                                stop_date=stop_date,
                                limit_mb=app.limit_mb,
                                passwords=app.passwords,
                                tp_type=app.tp_type)

def _query_table(req: dict, start_date: datetime, stop_date: datetime) -> list:

    res = []

    # Currently, only a single table target supported
    elm = req["targets"][0]
    if len(req["targets"]) > 1:
        logger.warning(f"Table query with multiple targets not supported")

    # Decode target
    target_req = _json_decode_target(elm["target"])
    if target_req is None:
        logger.warning(f"Failed to query target: {elm['target']}")
        return res

    # Fields required for table
    if "device" in target_req:

        # Get request type, data or info
        request_type = target_req.get("type", RequestType.DATA)

        if request_type is RequestType.DATA:
            res = table_raw_data(fs=app.fs,
                             device=target_req["device"],
                             start_date=start_date,
                             stop_date=stop_date,
                             max_data_points=req["maxDataPoints"],
                             passwords=app.passwords)

        elif request_type is RequestType.INFO:
            res = table_fs(fs=app.fs,
                           device=target_req["device"],
                           start_date=start_date,
                           stop_date=stop_date,
                           max_data_points=req["maxDataPoints"],
                           passwords=app.passwords)

    return res
