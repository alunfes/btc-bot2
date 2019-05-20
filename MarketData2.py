import threading
import pandas as pd
import numpy as np
import time
import copy
from datetime import datetime
from OneMinutesData import OneMinutesData
from CryptowatchDataGetter import CryptowatchDataGetter
from SystemFlg import SystemFlg
import numpy as np
import random
import pyti
from pyti.bollinger_bands import percent_bandwidth as pb
from pyti.exponential_moving_average import exponential_moving_average as ema
from numba import jit, f8, i8, b1, void

class MarketData2:
    @classmethod
    def initialize_from_bot_csv(cls, num_term, window_term, future_side_period, future_side_kijun, initial_data_vol):
        cls.num_term = num_term
        cls.window_term = window_term
        cls.index_of_last_calc = 0
        cls.future_side_period = future_side_period
        cls.future_side_kijun = future_side_kijun
        cls.ohlc_bot = OneMinutesData()
        cls.ohlc_bot.initialize()
        cls.ohlc_bot = cls.read_from_csv('./Data/one_min_data.csv')
        cls.ohlc_bot.del_data(initial_data_vol)
        cls.index_of_last_calc = len(cls.ohlc_bot.dt)-1
        #cls.ohlc_bot = cls.calc_ma3(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_ma_kairi3(cls.num_term,cls.window_term,cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_momentum3(cls.num_term,cls.window_term,cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_rsi3(cls.num_term,cls.window_term,cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_percent_bandwidth(cls.num_term,cls.window_term,cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_future_side(cls.future_side_period, cls.future_side_kijun, cls.ohlc_bot)

    @classmethod
    def split_min_data_to_tick(cls):
        tick = []
        split_num = 60
        for i in range(len(md.ohlc_bot.dt)):
            width = float(md.ohlc_bot.high[i] - md.ohlc_bot.low[i]) / float(split_num)
            sec_width = 0
            om_tick = []
            if md.ohlc_bot.open[i] < md.ohlc_bot.close[i]:  # open, low, high, close
                ol = md.ohlc_bot.open[i] - md.ohlc_bot.low[i]
                lh = md.ohlc_bot.high[i] - md.ohlc_bot.low[i]
                hc = md.ohlc_bot.high[i] - md.ohlc_bot.close[i]
                sec_width = (ol + lh + hc) / split_num
                print('ol={},lh={},hc={}'.format(ol, lh, hc))
                print('secw={}'.format(sec_width))
                om_tick.extend(list(np.arange(md.ohlc_bot.open[i], md.ohlc_bot.low[i], -sec_width)))
                om_tick.extend(list(np.arange(md.ohlc_bot.low[i], md.ohlc_bot.high[i], sec_width)))
                om_tick.extend(list(np.arange(md.ohlc_bot.high[i], md.ohlc_bot.close[i], -sec_width)))
                tick.extend(om_tick)
            else:  # open, high, low, close
                oh = md.ohlc_bot.high[i] - md.ohlc_bot.open[i]
                hl = md.ohlc_bot.high[i] - md.ohlc_bot.low[i]
                lc = md.ohlc_bot.close[i] - md.ohlc_bot.low[i]
                sec_width = (oh + hl + lc) / split_num
                print('oh={},hl={},lc={}'.format(oh, hl, lc))
                print('secw={}'.format(sec_width))
                om_tick.extend(list(np.arange(md.ohlc_bot.open[i], md.ohlc_bot.high[i], sec_width)))
                om_tick.extend(list(np.arange(md.ohlc_bot.high[i], md.ohlc_bot.low[i], -sec_width)))
                om_tick.extend(list(np.arange(md.ohlc_bot.low[i], md.ohlc_bot.close[i], sec_width)))
                tick.extend(om_tick)
        return tick
            

    @classmethod
    def initialize_from_omd(cls, num_term, window_term, future_period, future_kijun, omd:OneMinutesData):
        cls.num_term = num_term
        cls.window_term = window_term
        cls.num_term = num_term * window_term
        cls.future_side_period = future_period
        cls.future_side_kijun = future_kijun
        cls.ohlc_bot = omd
        cls.ohlc_bot = cls.calc_ma2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_ma_kairi2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_momentum2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_rsi2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_percent_bandwidth(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_future_side(cls.future_side_period, cls.future_side_kijun, cls.ohlc_bot)


    @classmethod
    def read_from_csv(cls, file_name):
        ohlc = OneMinutesData()
        ohlc.initialize()
        #df = pd.read_csv(file_name, skipfooter=17000)
        df = pd.read_csv(file_name)
        ohlc.dt = list(df['dt'])
        ohlc.unix_time = list(df['unix_time'])
        ohlc.open = list(df['open'])
        ohlc.high = list(df['high'])
        ohlc.low = list(df['low'])
        ohlc.close = list(df['close'])
        ohlc.size = list(df['size'])
        return ohlc

    @classmethod
    def update_ohlc_index_for_bot(cls, tmp_ohlc:OneMinutesData):
        from_ind = -1
        for i in range(len(tmp_ohlc.unix_time)):
            if tmp_ohlc.unix_time[i] > cls.ohlc_bot.unix_time[len(cls.ohlc_bot.unix_time)-1]:
                from_ind = i
                break
        if from_ind > 0:
            cls.ohlc_bot.dt.extend(tmp_ohlc.dt[from_ind:])
            cls.ohlc_bot.unix_time.extend(tmp_ohlc.unix_time[from_ind:])
            cls.ohlc_bot.open.extend(tmp_ohlc.open[from_ind:])
            cls.ohlc_bot.high.extend(tmp_ohlc.high[from_ind:])
            cls.ohlc_bot.low.extend(tmp_ohlc.low[from_ind:])
            cls.ohlc_bot.close.extend(tmp_ohlc.close[from_ind:])
            cls.ohlc_bot.size.extend(tmp_ohlc.size[from_ind:])
            cls.ohlc_bot = cls.update_ma2(cls.ohlc_bot)
        else:
            print('tmp data has no new record!')

    @classmethod
    def update_ohlc_index_for_bot2(cls):
        cls.update_ma2()
        cls.update_ma_kairi2()
        cls.update_momentum2()
        cls.update_rsi2()
        cls.update_percent_bandwidth()


    @classmethod
    def generate_df(cls, ohlc):
        end = len(ohlc.close) - cls.future_side_period
        df = pd.DataFrame()
        df = df.assign(dt=ohlc.dt[cls.num_term:end])
        df = df.assign(open=ohlc.open[cls.num_term:end])
        df = df.assign(high=ohlc.high[cls.num_term:end])
        df = df.assign(low=ohlc.low[cls.num_term:end])
        df = df.assign(close=ohlc.close[cls.num_term:end])
        df = df.assign(size=ohlc.size[cls.num_term:end])
        for k in ohlc.ma_kairi:
            col = 'ma_kairi' + str(k)
            df = df.assign(col=ohlc.ma_kairi[k][cls.num_term:end])
            df.rename(columns={'col': col}, inplace=True)
        for k in ohlc.rsi:
            col = 'rsi' + str(k)
            df = df.assign(col=ohlc.rsi[k][cls.num_term:end])
            df.rename(columns={'col': col}, inplace=True)
        for k in ohlc.momentum:
            col = 'mom' + str(k)
            df = df.assign(col=ohlc.momentum[k][cls.num_term:end])
            df.rename(columns={'col': col}, inplace=True)
        df = df.assign(future_side=ohlc.future_side[cls.num_term:])
        print('future side unique val')
        print(df['future_side'].value_counts(dropna=False, normalize=True))
        return df

    @classmethod
    def __check_ma_kairi(cls,df:pd.DataFrame):
        key = ''
        for i in range(100):
            if 'ma_kairi'+str(i) in df.columns:
                key = 'ma_kairi'+str(i)
                break
        #df[key] random.randrange(10)
    
    @classmethod
    def generate_df_for_bot(cls, ohlc:OneMinutesData):
        df = pd.DataFrame()
        df = df.assign(dt=ohlc.dt[-1:])
        df = df.assign(open=ohlc.open[-1:])
        df = df.assign(high=ohlc.high[-1:])
        df = df.assign(low=ohlc.low[-1:])
        df = df.assign(close=ohlc.close[-1:])
        df = df.assign(size=ohlc.size[-1:])
        for k in ohlc.ma_kairi:
            col = 'ma_kairi' + str(k)
            df = df.assign(col=ohlc.ma_kairi[k][-1:])
            df.rename(columns={'col': col}, inplace=True)
        for k in ohlc.rsi:
            col = 'rsi' + str(k)
            df = df.assign(col=ohlc.rsi[k][-1:])
            df.rename(columns={'col': col}, inplace=True)
        for k in ohlc.momentum:
            col = 'mom' + str(k)
            df = df.assign(col=ohlc.momentum[k][-1:])
            df.rename(columns={'col': col}, inplace=True)
        return df

    '''
    future_side should be checked assuming real use case as a prediction
    predict using ohlc data so should calc using next 1m ohlc
    '''
    @classmethod
    def calc_future_side(cls, future_side_period, future_side_kijun, ohlc):
        for i in range(len(ohlc.close) - future_side_period):
            buy_max = 0
            sell_max = 0
            for j in range(i, i + future_side_period):
                buy_max = max(buy_max, ohlc.high[j+1] - ohlc.close[i])
                sell_max = max(sell_max, ohlc.close[i] - ohlc.low[j+1])
            if buy_max >= future_side_kijun and sell_max >= future_side_kijun:
                ohlc.future_side.append('both')
            elif buy_max >= future_side_kijun and sell_max < future_side_kijun:
                ohlc.future_side.append('buy')
            elif buy_max < future_side_kijun and sell_max >= future_side_kijun:
                ohlc.future_side.append('sell')
            elif buy_max < future_side_kijun and sell_max < future_side_kijun:
                ohlc.future_side.append('no')
        return ohlc

    @classmethod
    def generate_tick_data(cls,ohlc):
        tick = []
        split_num = 60
        for i in range(len(ohlc.dt)):
            sec_width = 0
            om_tick = []
            if ohlc.open[i] < ohlc.close[i]:  # open, low, high, close
                ol = ohlc.open[i] - ohlc.low[i]
                lh = ohlc.high[i] - ohlc.low[i]
                hc = ohlc.high[i] - ohlc.close[i]
                sec_width = (ol + lh + hc) / split_num
                om_tick.extend(list(np.round(np.linspace(ohlc.open[i], ohlc.low[i], round(ol / sec_width)))))
                om_tick.extend(list(np.round(np.linspace(ohlc.low[i], ohlc.high[i], round(lh / sec_width)))))
                om_tick.extend(
                    list(np.round(np.linspace(ohlc.high[i], ohlc.close[i], round(hc / sec_width)))))
            else:  # open, high, low, close
                oh = ohlc.high[i] - ohlc.open[i]
                hl = ohlc.high[i] - ohlc.low[i]
                lc = ohlc.close[i] - ohlc.low[i]
                sec_width = (oh + hl + lc) / split_num
                om_tick.extend(list(np.round(np.linspace(ohlc.open[i], ohlc.high[i], round(oh / sec_width)))))
                om_tick.extend(list(np.round(np.linspace(ohlc.high[i], ohlc.low[i], round(hl / sec_width)))))
                om_tick.extend(list(np.round(np.linspace(ohlc.low[i], ohlc.close[i], round(lc / sec_width)))))
            tick.extend(om_tick)
        return tick

    @classmethod
    def calc_ema(cls, ohlc):
        num = round(cls.num_term / cls.window_term)
        if num >1:
            for i in range(num):
                term = cls.window_term * (i+ 1)
                if term > 2:
                    ohlc.ema[term] = list(ema(ohlc.close, term))
        return ohlc


    @classmethod
    def calc_percent_bandwidth(cls, ohlc):
        num = round(cls.num_term / cls.window_term)
        if num >1:
            for i in range(num):
                term = cls.window_term * (i+ 1)
                if term > 2:
                    ohlc.percent_bandwidth[term] = list(pb(ohlc.close, term))
        return ohlc

    @classmethod
    def update_percent_bandwidth(cls):
        pass



    @classmethod
    def calc_ma3(cls, ohlc):
        num = round(cls.num_term / cls.window_term)
        if num >1:
            for i in range(num):
                term = cls.window_term * (i+ 1)
                if term > 1:
                    ohlc.ma[term] = list(pd.Series(ohlc.close).rolling(window=term).mean())
        return ohlc

    @classmethod
    def calc_ma2(cls, ohlc):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            if term > 1:
                ohlc.ma[term] = list(pd.Series(ohlc.close).rolling(window=term).mean())
        return ohlc


    @classmethod
    def update_ma3(cls):
        num = round(cls.num_term / cls.window_term)
        close = cls.ohlc_bot.close[1]
        if num >1:
            for i in range(num):
                term = cls.window_term * (i+ 1)
                if term > 1:
                    pass
                    #ohlc.ma[term] = list(pd.Series(ohlc.close).rolling(window=term).mean())
                    #cls.ohlc_bot.ma[term].extemd()


    @classmethod
    def update_ma2(cls):
        for i in range(cls.num_term):
            term =  (i+1) * cls.window_term
            if term > 1:
                close_con = cls.ohlc_bot.close[len(cls.ohlc_bot.close) - term - (len(cls.ohlc_bot.ma[term]) - len(cls.ohlc_bot.close) + 1):]
                updates = list(pd.Series(close_con).rolling(window=term).mean().dropna())
                cls.ohlc_bot.ma[term].extend(updates)


    @classmethod
    def calc_ma_kairi3(cls, ohlc):
        num = round(cls.num_term / cls.window_term)
        if num >1:
            for i in range(num):
                term = cls.window_term * (i+ 1)
                if term > 1:
                    ohlc.ma_kairi[term] = list([x / y for (x,y) in zip(ohlc.close, ohlc.ma[term])])
        return ohlc

    @classmethod
    def calc_ma_kairi2(cls, ohlc):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            if term > 1:
                ohlc.ma_kairi[term] = list([x / y for (x,y) in zip(ohlc.close, ohlc.ma[term])])
        return ohlc

    @classmethod
    def update_ma_kairi2(cls):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            if term > 1:
                close_con = cls.ohlc_bot.close[len(cls.ohlc_bot.ma_kairi[term]) - len(cls.ohlc_bot.close):]
                ma_con = cls.ohlc_bot.ma[term][len(cls.ohlc_bot.ma_kairi[term]) - len(cls.ohlc_bot.ma[term]):]
                cls.ohlc_bot.ma_kairi[term].extend(list([x / y for (x, y) in zip(close_con, ma_con)]))


    @classmethod
    def calc_momentum3(cls, ohlc):
        num = round(cls.num_term / cls.window_term)
        if num >1:
            for i in range(num):
                term = cls.window_term * (i+ 1)
                if term > 1:
                    ohlc.momentum[term] = list(pd.Series(ohlc.close).diff(term-1))
        return ohlc

    @classmethod
    def calc_momentum2(cls, ohlc):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            if term > 1:
                ohlc.momentum[term] = list(pd.Series(ohlc.close).diff(term-1))
        return ohlc

    @classmethod
    def update_momentum2(cls):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            if term > 1:
                close_con = cls.ohlc_bot.close[len(cls.ohlc_bot.close) - term - (len(cls.ohlc_bot.momentum[term]) - len(cls.ohlc_bot.close)+1)+1:]
                cls.ohlc_bot.momentum[term].extend(list(pd.Series(close_con).diff(term - 1).dropna()))


    @classmethod
    def calc_rsi3(cls, ohlc):
        num = round(cls.num_term / cls.window_term)
        if num >1:
            for i in range(num):
                term = window * (i+ 1)
                if term > 1:
                    diff = pd.Series([x - y for (x,y) in zip(ohlc.close, ohlc.open)])
                    up, down = diff.copy(), diff.copy()
                    up[up < 0] = 0
                    down[down > 0] = 0
                    up_sma = up.rolling(window = term, center = False).mean()
                    down_sma = down.abs().rolling(window=term, center=False).mean()
                    ohlc.rsi[term] = list(100.0 - (100.0 / (1.0 + up_sma / down_sma)))
        return ohlc

    @classmethod
    def calc_rsi2(cls, ohlc):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            if term > 1:
                diff = pd.Series([x - y for (x,y) in zip(ohlc.close, ohlc.open)])
                up, down = diff.copy(), diff.copy()
                up[up < 0] = 0
                down[down > 0] = 0
                up_sma = up.rolling(window = term, center = False).mean()
                down_sma = down.abs().rolling(window=term, center=False).mean()
                ohlc.rsi[term] = list(100.0 - (100.0 / (1.0 + up_sma / down_sma)))
        return ohlc

    @classmethod
    def update_rsi2(cls):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            if term > 1:
                close_con = cls.ohlc_bot.close[len(cls.ohlc_bot.close) - len(cls.ohlc_bot.rsi):]
                open_con = cls.ohlc_bot.open[len(cls.ohlc_bot.open) - len(cls.ohlc_bot.rsi):]
                diff = pd.Series([x - y for (x, y) in zip(close_con, open_con)])
                up, down = diff.copy(), diff.copy()
                up[up < 0] = 0
                down[down > 0] = 0
                up_sma = up.rolling(window=term, center=False).mean()
                down_sma = down.abs().rolling(window=term, center=False).mean()
                cls.ohlc_bot.rsi[term].extend(list(100.0 - (100.0 / (1.0 + up_sma / down_sma))))

    @classmethod
    def update_ma(cls):
        for i in range(cls.num_term):
            term = i + 5
            ma = []
            for j in range(len(cls.ohlc_bot.close) - len(cls.ohlc_bot.ma[term])):
                fromind = len(cls.ohlc_bot.ma[term]) - term + j + 1
                toind = len(cls.ohlc_bot.ma[term]) + j + 1
                nli = cls.ohlc_bot.close[fromind:toind]
                ma.append(sum(nli) / float(term))
            cls.ohlc_bot.ma[term].extend(ma)

    @classmethod
    def update_ma_kairi(cls):
        for i in range(cls.num_term):
            term = i + 5
            kairi = []
            for j in range(len(cls.ohlc_bot.close) - len(cls.ohlc_bot.ma_kairi[term])):
                ind = len(cls.ohlc_bot.ma_kairi[term]) + j
                kairi.append(float(cls.ohlc_bot.close[ind]) / float(cls.ohlc_bot.ma[term][ind]))
            cls.ohlc_bot.ma_kairi[term].extend(kairi)

    @classmethod
    def update_momentum(cls):
        for i in range(cls.num_term):
            term = i + 5
            mom = []
            for j in range(len(cls.ohlc_bot.close) - len(cls.ohlc_bot.momentum[term])):
                mom.append(cls.ohlc_bot.close[len(cls.ohlc_bot.momentum[term] + j)] -
                           cls.ohlc_bot.close[len(cls.ohlc_bot.momentum[term] + j + term)])
            cls.ohlc_bot.momentum[term].extend(mom)

    @classmethod
    def update_rsi(cls):
        for i in range(cls.num_term):
            term = i + 5
            rsi = []
            for j in range(len(cls.ohlc_bot.close) - len(cls.ohlc_bot.rsi[term])):
                up_sum = 0
                down_sum =0
                ind = len(cls.ohlc_bot.rsi[term]) + j
                for k in range(term):
                    change = cls.ohlc_bot.close[ind - k] - cls.ohlc_bot.open[ind -k]
                    if change >= 0:
                        up_sum += change
                    else:
                        down_sum += abs(change)
                if up_sum == 0 and down_sum == 0:
                    rsi.append(0)
                else:
                    rsi.append(up_sum / (up_sum + down_sum))
                cls.ohlc_bot.rsi[term].extend(rsi)


if __name__ == '__main__':
    print('initializing data')
    MarketData2.initialize_from_bot_csv(10,1,1,500,500)
    df =MarketData2.generate_df(MarketData2.ohlc_bot)
    df.to_csv('./generated_df.csv')
'''
@classmethod
def read_from_csv(cls, ohlc):
    with cls.data_lock:
        ohlc.initialize()
        df = pd.read_csv('/content/drive/My Drive/one_min_data.csv')
        ohlc.dt = list(df['dt'])
        ohlc.unix_time = list(df['unix_time'])
        ohlc.open = list(df['open'])
        ohlc.high = list(df['high'])
        ohlc.low = list(df['low'])
        ohlc.close = list(df['close'])
        ohlc.size = list(df['size'])
        return ohlc
'''




