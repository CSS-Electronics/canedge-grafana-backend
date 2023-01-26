from dataclasses import dataclass
from can_decoder import SignalDB
from itertools import groupby
import numpy as np
import pandas as pd
import canedge_browser
import can_decoder
import mdf_iter
from datetime import datetime
from utils import MultiFrameDecoder

from canedge_datasource import cache
from canedge_datasource.enums import CanedgeInterface, CanedgeChannel, SampleMethod

import logging
logger = logging.getLogger(__name__)


@dataclass
class SignalQuery:

    def __str__(self):
        return (f"{self.refid}, {self.target}, {self.device}, {self.itf.name}, {self.chn.name}, {self.signal_name}, "
                f"{self.interval_ms}, {self.method.name}")

    refid: str
    target: str
    device: str
    itf: CanedgeInterface
    chn: CanedgeChannel
    db: SignalDB
    signal_name: str
    interval_ms: int
    method: SampleMethod = SampleMethod.NEAREST


def table_fs(fs, device, start_date: datetime, stop_date: datetime, max_data_points, passwords) -> list:
    """
    Returns a list of log files as table
    """

    # Find log files
    log_files = canedge_browser.get_log_files(fs, device, start_date=start_date, stop_date=stop_date,
                                              passwords=passwords)

    rows = []
    for log_file in log_files:

        # Get file start time
        with fs.open(log_file, "rb") as handle:
            mdf_file = mdf_iter.MdfFile(handle, passwords=passwords)
            start_epoch_ms = mdf_file.get_first_measurement() / 1000000
            meta_data = mdf_file.get_metadata()

        # Get size
        size_mb = fs.size(log_file) >> 20
        session = meta_data.get("HDcomment.File Information.session", {}).get("value_raw")
        split = meta_data.get("HDcomment.File Information.split", {}).get("value_raw")
        config_crc = meta_data.get("HDcomment.Device Information.config crc32 checksum", {}).get("value_raw")
        hw_rev = meta_data.get("HDcomment.Device Information.hardware version", {}).get("value_raw")
        fw_rev = meta_data.get("HDcomment.Device Information.firmware version", {}).get("value_raw")
        storage_free = meta_data.get("HDcomment.Device Information.storage free", {}).get("value_raw")
        storage_total = meta_data.get("HDcomment.Device Information.storage total", {}).get("value_raw")
        comment = meta_data.get("HDcomment.File Information.comment", {}).get("value_raw").strip()

        storage_mb = ""
        if storage_free is not None and storage_total is not None:
            storage_mb = f"{int(storage_total)-int(storage_free)>>10}/{int(storage_total)>>10}"

        rows.append([start_epoch_ms, device, session, split, size_mb, config_crc, hw_rev, fw_rev, storage_mb, log_file, comment])

        # {"type": "info", "device":"79A2DD1A"}

        if len(rows) >= max_data_points:
            break

    res = [
        {
                "type": "table",
                "columns": [
                    {"text": "TIME", "type": "time"},
                    {"text": "DEVICE", "type": "string"},
                    {"text": "SESSION", "type": "string"},
                    {"text": "SPLIT", "type": "string"},
                    {"text": "SIZE [MB]", "type": "string"},
                    {"text": "CONFIG CRC", "type": "string"},
                    {"text": "HW", "type": "string"},
                    {"text": "FW", "type": "string"},
                    {"text": "STORAGE [MB]", "type": "string"},
                    {"text": "NAME", "type": "string"},
                    {"text": "META", "type": "string"},
                ],
                "rows": rows
            }
        ]
    return res


def table_raw_data(fs, device, start_date: datetime, stop_date: datetime, max_data_points, passwords) -> list:
    """
    Returns raw log file data as table
    """

    # Find log files
    log_files = canedge_browser.get_log_files(fs, device, start_date=start_date, stop_date=stop_date,
                                              passwords=passwords)

    # Load log files one at a time until max_data_points
    df_raw = pd.DataFrame()
    for log_file in log_files:

        _, df_raw_can, df_raw_lin, = _load_log_file(fs, log_file, [CanedgeInterface.CAN, CanedgeInterface.LIN],
                                                    passwords)

        # Add interface column
        df_raw_can['ITF'] = "CAN"
        df_raw_lin['ITF'] = "LIN"

        # Lin set extended to 0
        df_raw_lin['IDE'] = 0

        # Merge data frames
        df_raw_chunk = pd.concat([df_raw_can, df_raw_lin])

        # Keep only selected time interval (files may contain a bit more at both ends)
        df_raw_chunk = df_raw_chunk.loc[start_date:stop_date]

        # Append
        df_raw = pd.concat([df_raw, df_raw_chunk])

        # Max data points reached?
        if len(df_raw) >= max_data_points:
            break

    # Any data in time interval?
    if len(df_raw) == 0:
        return None

    # Reset the index to get the timestamp as column
    df_raw.reset_index(inplace=True)

    # Keep only selected columns
    df_raw = df_raw[["TimeStamp", 'ITF', 'BusChannel', 'ID', 'IDE', 'DataLength', 'DataBytes']]

    # Rename columns
    df_raw.rename(columns={"TimeStamp": "TIME", "BusChannel": "CHN", "DataLength": "NOB", 'DataBytes': "DATA"},
                  inplace=True)

    # Cut to max data points
    df_raw = df_raw[0:max_data_points]

    # Change from datetime to epoch
    df_raw['TIME'] = df_raw['TIME'].astype(np.int64) / 10 ** 6

    # Change "Databytes" from array to hex string
    df_raw['DATA'] = df_raw['DATA'].apply(lambda data: ' '.join('{:02X}'.format(x) for x in data))

    # Column names and types
    columns = [{"text": x, "type": "time" if x == "TIME" else "string"} for x in list(df_raw.columns)]

    # Return formatted output
    return [{"type": "table", "columns": columns, "rows": df_raw.values.tolist()}]


def time_series_phy_data(fs, signal_queries: [SignalQuery], start_date: datetime, stop_date: datetime, limit_mb,
                         passwords, tp_type) -> dict:
    """
    Returns time series based on a list of signal queries.

    The function is optimized towards:
    - Low memory usage (only one file loaded at a time).
    - As few decoding runs as possible (time expensive)

    For each device, a log file is only loaded once. To obtain this, the signal requests are first grouped by device ID.

    The decoder takes one db and assumes that this should be applied all entries (regardless of channel and interface).
    As a result, it is needed to run the decoder for each combination of db, channel and interface.
    Signals from the same channel and interface can be grouped to process all in one run (applied after device grouping)

    Returns as a list of dicts. Each dict contains the signal "target" name and data points as a list of value (float/str)
    and timestamp (float) tuples.

    e.g.
    [
        {'target': 'A', 'datapoints': [(0.1, 1603895728164.1)]},
        {'target': 'B', 'datapoints': [(1.1, 1603895728164.1), (1.2, 1603895729164.15)]},
        {'target': 'C', 'datapoints': [(3.1, 1603895728164.1), (3.2, 1603895729164.15), (3.3, 1603895729164.24)]}
    ]
    """

    # Init response to make sure that we respond to all targets, even if without data points
    result = [{'refId': x.refid, 'target': x.target, 'datapoints': []} for x in signal_queries]

    # Keep track on how much data has been processed (in MB)
    data_processed_mb = 0

    # Group the signal queries by device, such that files from the same device needs to be loaded only once
    for device, device_group in groupby(signal_queries, lambda x: x.device):

        device_group = list(device_group)

        # Find log files
        log_files = canedge_browser.get_log_files(fs, device, start_date=start_date, stop_date=stop_date,
                                                  passwords=passwords)

        # Load log files one at a time (to reduce memory usage)
        session_previous = None
        for log_file in log_files:

            # Check if log file is in new session
            _, session_current, _, _ = fs.path_to_pars(log_file)
            new_session = False
            if session_previous is not None and session_previous != session_current:
                new_session = True
            session_previous = session_current

            # Get size of file
            file_size_mb = fs.stat(log_file)["size"] >> 20

            # Check if we have reached the limit of data processed in MB
            if data_processed_mb + file_size_mb > limit_mb:
                logger.info(f"File: {log_file} - Skipping (limit {limit_mb} MB)")
                continue
            logger.info(f"File: {log_file}")

            # Update size of data processed
            data_processed_mb += file_size_mb

            # TODO: caching can be improved on by taking log file and signal - such that the cached data contain the
            # decoded signals (with max time resolution). Currently, the cache contains all data, which does not improve
            # loading times significantly (and takes a lot of memory)
            start_epoch, df_raw_can, df_raw_lin = _load_log_file(fs, log_file, [x.itf for x in device_group], passwords)

            # Keep only selected time interval (files may contain a more at both ends). Do this early to process as
            # little data as possible
            df_raw_can = df_raw_can.loc[start_date:stop_date]
            df_raw_lin = df_raw_lin.loc[start_date:stop_date]

            # If no data, continue to next file
            if len(df_raw_can) == 0 and len(df_raw_lin) == 0:
                continue

            # Group queries using the same db, interface and channel (to minimize the number of decoding runs)
            for (itf, chn, db), decode_group in groupby(device_group, lambda x: (x.itf, x.chn, x.db)):

                decode_group = list(decode_group)

                # Keep only selected interface (only signals from the same interface are grouped)
                df_raw = df_raw_can if itf == CanedgeInterface.CAN else df_raw_lin

                # Keep only selected channel
                df_raw = df_raw.loc[df_raw['BusChannel'] == int(chn)]

                if df_raw.empty:
                    continue

                # If IDE missing (LIN) add dummy allow decoding
                if 'IDE' not in df_raw:
                    df_raw['IDE'] = 0

                # Filter out IDs not used before the costly decoding step (bit 32 cleared). For simplicity, does not
                # differentiate standard and extended. Result is potentially unused IDs passed for decoding if overlaps
                if db.protocol == "J1939":
                    #TODO Find out how to do pre-filtering on PGNs to speed up J1939 decoding
                    pass
                else:
                    df_raw = df_raw[df_raw['ID'].isin([x & 0x7FFFFFFF for x in db.frames.keys()])]
                    # TODO optimize by using requested signals to create a smaller subset DBC and filter by that

                if tp_type != "":
                    # Decode after first re-segmenting CAN data according to TP type (uds, j1939, nmea)
                    #TODO Optimize for speed
                    tp = MultiFrameDecoder(tp_type)
                    df_raw = tp.combine_tp_frames(df_raw)

                df_phys_temp = [] 
                for length, group in df_raw.groupby("DataLength"):
                    df_phys_group = can_decoder.DataFrameDecoder(db).decode_frame(group)

                    if 'Signal' not in df_phys_group.columns:
                        continue

                    df_phys_temp.append(df_phys_group)

                if len(df_phys_temp) > 0:
                    df_phys = pd.concat(df_phys_temp,ignore_index=False).sort_index()
                else:
                    df_phys = pd.DataFrame()

                # commented out the original option of a "clean" decoding due to lack of support for mixed DLC rows in df_raw
                # df_phys = can_decoder.DataFrameDecoder(db).decode_frame(df_raw)


                # Check if output contains any signals
                if 'Signal' not in df_phys.columns:
                    continue

                # Keep only requested signals
                df_phys = df_phys[df_phys['Signal'].isin([x.signal_name for x in decode_group])]

                # Drop unused columns
                df_phys.drop(['CAN ID', 'Raw Value'], axis=1, inplace=True)

                # Resample each signal using the specific method and interval.
                # Making sure that only existing/real data points are included in the output (no interpolations etc).
                for signal_group in decode_group:

                    # "Backup" the original timestamps, such that these can be used after resampling
                    df_phys['time_orig'] = df_phys.index

                    # Extract the signal
                    df_phys_signal = df_phys.loc[df_phys['Signal'] == signal_group.signal_name]

                    # Pick the min, max or nearest. This picks a real data value but potentially a "fake" timestamp
                    interval_ms = signal_group.interval_ms
                    if signal_group.method == SampleMethod.MIN:
                        df_phys_signal_resample = df_phys_signal.resample(f"{interval_ms}ms").min()
                    elif signal_group.method == SampleMethod.MAX:
                        df_phys_signal_resample = df_phys_signal.resample(f"{interval_ms}ms").max()
                    else:
                        df_phys_signal_resample = df_phys_signal.resample(f"{interval_ms}ms").nearest()

                    # The "original" time was also resampled. Use this to restore true data points.
                    # Drop duplicates and nans (duplicates were potentially created during "nearest" resampling)
                    # This also makes sure that data is never up-sampled
                    df_phys_signal_resample.drop_duplicates(subset='time_orig', inplace=True)
                    df_phys_signal_resample.dropna(axis=0, how='any', inplace=True)

                    # Timestamps and values to list
                    timestamps = (df_phys_signal_resample["time_orig"].astype(np.int64) / 10 ** 6).tolist()
                    values = df_phys_signal_resample["Physical Value"].values.tolist()

                    # Get the list index of the result to update
                    result_index = [idx for idx, value in enumerate(result) if value['target'] == signal_group.target][0]

                    # If new session, insert a None/null data point to indicate that data is not continuous
                    if new_session:
                        result[result_index]["datapoints"].extend([[None, None]])

                    # Update result with additional datapoints
                    result[result_index]["datapoints"].extend(list(zip(values, timestamps)))

    return result


def _load_log_file(fs, file, itf_used, passwords):

    # As local function to be able to cache result
    @cache.memoize(timeout=50)
    def _load_log_file_cache(file_in, itf_used_in, passwords_in):
        with fs.open(file_in, "rb") as handle:
            mdf_file = mdf_iter.MdfFile(handle, passwords=passwords_in)

            # Get log file start time
            start_epoch = datetime.utcfromtimestamp(mdf_file.get_first_measurement() / 1000000000)

            # Load only the interfaces which are used
            df_raw_can_local = mdf_file.get_data_frame() if CanedgeInterface.CAN in itf_used_in else pd.DataFrame()
            df_raw_lin_local = mdf_file.get_data_frame_lin() if CanedgeInterface.LIN in itf_used_in else pd.DataFrame()

        return start_epoch, df_raw_can_local, df_raw_lin_local

    return _load_log_file_cache(file, itf_used, passwords)
