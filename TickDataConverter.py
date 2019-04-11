import pandas as pd
import datetime
import os


class TickDataConverter:
    def convert_tick_to_onemin(self):
        i = 0
        for chunk in pd.read_csv("./tick.csv", chunksize=100000, header=None):
            dt = chunk.iloc[:, :1].applymap(datetime.datetime.fromtimestamp)
            price = chunk.iloc[:, 1:2]
            size = chunk.iloc[:, 2:3]
            df = pd.concat([dt, price, size], axis=1)
            df.columns = ['datetime', 'price', 'size']
            dict = df.to_dict(orient='records')
            print('inserted ' + str(i * 100000))