from datetime import datetime
import can_decoder
import canedge_browser
import pytest
import pytz

from canedge_datasource.enums import CanedgeInterface, CanedgeChannel, SampleMethod
from canedge_datasource.query import get_time_series, SignalQuery


class TestCanedgeTimeSeries(object):

    @pytest.fixture
    def fs(self):
        fs = canedge_browser.LocalFileSystem(base_path="root/")
        return fs

    def test_time_series(self, fs):

        obd = can_decoder.load_dbc("root/obd.dbc")

        signal_name = "S1_PID_0D_VehicleSpeed"
        start_date = datetime(year=2020, month=8, day=4, hour=10).replace(tzinfo=pytz.UTC)
        stop_date = datetime(year=2022, month=9, day=9, hour=10).replace(tzinfo=pytz.UTC)

        sampling_ms = 1000

        signal_queries = []

        signal_queries.append(SignalQuery(target="A",
                                          device="3BA199E2",
                                          itf=CanedgeInterface.CAN,
                                          chn=CanedgeChannel.CH1,
                                          db=obd,
                                          signal_name="S1_PID_0C_EngineRPM",
                                          interval_ms=sampling_ms,
                                          method=SampleMethod.NEAREST))

        signal_queries.append(SignalQuery(target="B",
                                          device="3BA199E2",
                                          itf=CanedgeInterface.CAN,
                                          chn=CanedgeChannel.CH1,
                                          db=obd,
                                          signal_name="S1_PID_0D_VehicleSpeed",
                                          interval_ms=sampling_ms,
                                          method=SampleMethod.NEAREST))

        signal_queries.append(SignalQuery(target="C",
                                          device="3BA199E2",
                                          itf=CanedgeInterface.CAN,
                                          chn=CanedgeChannel.CH2,
                                          db=obd,
                                          signal_name="S1_PID_0D_VehicleSpeed",
                                          interval_ms=sampling_ms,
                                          method=SampleMethod.NEAREST))

        signal_queries.append(SignalQuery(target="D",
                                          device="3BA199E2",
                                          itf=CanedgeInterface.CAN,
                                          chn=CanedgeChannel.CH2,
                                          db=obd,
                                          signal_name="S1_PID_0D_VehicleSpeed",
                                          interval_ms=sampling_ms,
                                          method=SampleMethod.NEAREST))

        signal_queries.append(SignalQuery(target="E",
                                          device="3BA199E2",
                                          itf=CanedgeInterface.LIN,
                                          chn=CanedgeChannel.CH1,
                                          db=obd,
                                          signal_name="S1_PID_0D_VehicleSpeed",
                                          interval_ms=sampling_ms,
                                          method=SampleMethod.NEAREST))

        signal_queries.append(SignalQuery(target="F",
                                          device="AABBCCDD",
                                          itf=CanedgeInterface.CAN,
                                          chn=CanedgeChannel.CH1,
                                          db=obd,
                                          signal_name="S1_PID_0D_VehicleSpeed",
                                          interval_ms=sampling_ms,
                                          method=SampleMethod.NEAREST))

        time_series = get_time_series(fs, signal_queries, start_date, stop_date)

        #assert start_date.timestamp() <= time_series[0][1] / 1000, "Start time error"
        #assert stop_date.timestamp() >= time_series[-1][1] / 1000, "Stop time error"
        #assert time_series[1][1] - time_series[0][1] >= interval_ms, "Period error"

        for a in time_series:
            print(a)

        #print(len(time_series))
        #print(time_series[0])
        #print(time_series[-1])
