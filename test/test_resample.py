from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import pytest


class TestResample(object):

    @pytest.mark.parametrize("interval_ms", [10, 50, 100, 115, 550, 755, 1000])
    def test_resampling(self, interval_ms):
        df = pd.DataFrame()

        df["time"] = [
            datetime(2000, 1, 1, 0, 0, 0, 100000),  # 100 ms
            datetime(2000, 1, 1, 0, 0, 0, 200000),
            datetime(2000, 1, 1, 0, 0, 0, 300000),
            datetime(2000, 1, 1, 0, 0, 0, 400000),
            datetime(2000, 1, 1, 0, 0, 0, 500000),
            datetime(2000, 1, 1, 0, 0, 0, 600000),
            datetime(2000, 1, 1, 0, 0, 0, 700000),
            datetime(2000, 1, 1, 0, 0, 0, 800000),
            datetime(2000, 1, 1, 0, 0, 0, 900000),
            datetime(2000, 1, 1, 0, 0, 1, 000000),  # 200 ms
            datetime(2000, 1, 1, 0, 0, 1, 200000),
            datetime(2000, 1, 1, 0, 0, 1, 400000),
            datetime(2000, 1, 1, 0, 0, 1, 600000),
            datetime(2000, 1, 1, 0, 0, 1, 800000),
            datetime(2000, 1, 1, 0, 0, 3, 000000),  # Missing 1 s, then 100 ms
            datetime(2000, 1, 1, 0, 0, 3, 100000),
            datetime(2000, 1, 1, 0, 0, 3, 200000),
            datetime(2000, 1, 1, 0, 0, 3, 300000),
            datetime(2000, 1, 1, 0, 0, 3, 400000),
            datetime(2000, 1, 1, 0, 0, 3, 500000),
            datetime(2000, 1, 1, 0, 0, 3, 600000),
            datetime(2000, 1, 1, 0, 0, 3, 700000),
            datetime(2000, 1, 1, 0, 0, 3, 800000),
            datetime(2000, 1, 1, 0, 0, 3, 900000)]

        df['time_orig'] = df['time']
        df["signal"] = np.sin(np.linspace(0, 2 * np.pi, len(df["time"])))

        df.set_index('time', inplace=True)

        df_resample = df.resample(rule=f"{interval_ms}ms").nearest()

        print(len(df))
        print(len(df_resample))
        df_resample.drop_duplicates(subset='time_orig', inplace=True)
        df_resample.dropna(axis=0, how='any', inplace=True)
        print(len(df_resample))

        assert len(df) >= len(df_resample)

        df.reset_index(inplace=True)
        df_resample.reset_index(inplace=True)

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.scatter(df['time'], df['signal'], s=30, c='b', label='Orig')
        ax.scatter(df_resample['time_orig'], df_resample['signal'], s=10, c='r', label='Resample')
        plt.xticks(rotation=90)
        plt.title(f"Interface: {interval_ms} ms")
        plt.show()

        #print(df)
        #print(df_resample)