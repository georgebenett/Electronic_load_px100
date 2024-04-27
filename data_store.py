from datetime import datetime
from os import path

from pandas import DataFrame
import pandas as pd


class DataStore:
    def __init__(self):
        self.reset()

    def __bool__(self):
        return len(self.lastrow) > 0

    def reset(self):
        self.lastrow = {}
        self.data = DataFrame()

    def append(self, row):
        tnow = datetime.now().isoformat(sep= ' ', timespec='milliseconds')
        print(f"{tnow} time_running={row['time']} is_on={row['is_on']} v={row['voltage']:.3f} i={row['current']:.3f}" \
            f" Ah={row['cap_ah']:.2f} board_temp={row['temp']} i_setpoint={row['set_current']}" \
            f" v_setpoint={row['set_voltage']} timer_setpoint={row['set_timer']}")
        self.lastrow = row
        # self.data = self.data.append(row, ignore_index=True)
        new_row_df = DataFrame([row])
        self.data = pd.concat([self.data, new_row_df], ignore_index=True)

    def write(self, basedir, prefix):
        filename = "{}_raw_{}.csv".format(prefix, datetime.now().strftime("%Y%m%d_%H%M%S"))
        full_path = path.join(basedir, filename)
        export_rows = self.data.drop_duplicates()
        if export_rows.shape[0]:
            print("Write RAW data to {}".format(path.relpath(full_path)))
            self.data.drop_duplicates().to_csv(full_path)
        else:
            print("no data")

    def plot(self, **args):
        return self.data.plot(**args)

    def lastval(self, key):
        return self.lastrow[key]
