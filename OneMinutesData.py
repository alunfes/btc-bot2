import pandas as pd
from numba import jit

class OneMinutesData:
    def initialize(self):
        self.num_crypto_data = 0
        self.unix_time = []
        self.dt = []
        self.open = []
        self.high = []
        self.low = []
        self.close = []
        self.size = []

        self.ma = {} #{term:[kairi]}
        self.ma_kairi = {}
        self.rsi = {}
        self.momentum = {}
        self.future_side = []

    @jit
    def cut_data(self, num_data):
        self.unix_time = self.unix_time[-num_data:]
        self.dt = self.dt[-num_data:]
        self.open = self.open[-num_data:]
        self.high = self.high[-num_data:]
        self.low = self.low[-num_data:]
        self.close = self.close[-num_data:]
        self.size = self.size[-num_data:]
        for k in self.ma:
            self.ma[k] = self.ma[k][-num_data:]
        for k in self.ma_kairi:
            self.ma_kairi[k] = self.ma_kairi[k][-num_data:]
        for k in self.momentum:
            self.momentum[k] = self.momentum[k][-num_data:]
        for k in self.rsi:
            self.rsi[k] = self.rsi[k][-num_data:]
        self.future_side = self.future_side[-num_data:]


    @jit
    def del_data(self, num_remain_data):
        del self.unix_time[:-num_remain_data]
        del self.dt[:-num_remain_data]
        del self.open[:-num_remain_data]
        del self.high[:-num_remain_data]
        del self.low[:-num_remain_data]
        del self.close[:-num_remain_data]
        del self.size[:-num_remain_data]
        for k in self.ma:
            del self.ma[k][:-num_remain_data]
        for k in self.ma_kairi:
            del self.ma_kairi[k][:-num_remain_data]
        for k in self.momentum:
            del self.momentum[k][:-num_remain_data]
        for k in self.rsi:
            del self.rsi[k][:-num_remain_data]
        del self.future_side[:-num_remain_data]

    @jit
    def add_and_pop(self, unix_time, dt, open, high, low, close, size):
        self.unix_time.append(unix_time)
        self.unix_time.pop(0)
        self.dt.append(dt)
        self.dt.pop(0)
        self.open.append(open)
        self.open.pop(0)
        self.high.append(high)
        self.high.pop(0)
        self.low.append(low)
        self.low.pop(0)
        self.close.append(close)
        self.close.pop(0)
        self.size.append(size)
        self.size.pop(0)





