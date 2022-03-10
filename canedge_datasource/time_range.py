from datetime import datetime
import pytz


def parse_time_range(start_date_str: str, stop_date_str: str) -> (datetime, datetime):
    """
    From / to times are provided in ISO8601 format without timezone information (naive). The timezone, however,
    is always UTC. By updating the timezone information the datetime objects become timezone aware.
    """
    start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
    stop_date = datetime.strptime(stop_date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)

    return start_date, stop_date
