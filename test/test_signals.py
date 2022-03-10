from datetime import datetime
import pandas as pd
import numpy as np
import pytest
import can_decoder

class TestSignals(object):

    def get_db_signals(self, db) -> list:
        def get_signal_recursive(signals) -> list:
            signal_list = []
            for item in signals:
                if isinstance(signals, dict):
                    signal_list.extend(get_signal_recursive(signals[item]))
                if isinstance(signals, list):
                    signal_list.append(item.name)
                    signal_list.extend(get_signal_recursive(item.signals))
            return signal_list
        signals = []
        for key, value in db.frames.items():
            signals.extend(get_signal_recursive(value.signals))
        return signals


    def test_signals(self):

        db = can_decoder.load_dbc("root/obd.dbc")

        a = self.get_db_signals(db)


        print(a)