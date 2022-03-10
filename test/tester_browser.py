from datetime import datetime, timezone, timedelta

import canedge_browser
from mdf_iter import mdf_iter

if __name__ == '__main__':

    fs = canedge_browser.LocalFileSystem(base_path="root")

    start_date = datetime(2021, 3, 26,  6, 0,  0, tzinfo=timezone.utc)
    stop_date =  datetime(2021, 3, 26, 18, 0,  0, tzinfo=timezone.utc)

    for offset in range(0, 2):

        print(f"Offset: {offset}")

        stop_date_offset = stop_date + timedelta(minutes=offset)

        log_files = canedge_browser.get_log_files(fs, "79A2DD1A", start_date=start_date, stop_date=stop_date)
        log_files.sort()

        for log_file in log_files:
            with fs.open(log_file, "rb") as handle:
                mdf_file = mdf_iter.MdfFile(handle)
                df_raw = mdf_file.get_data_frame()
                start_time = df_raw.head(1).index.values[0]
                print(f"{log_file}, {start_time}")



