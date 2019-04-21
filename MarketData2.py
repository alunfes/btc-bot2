import threading
import pandas as pd
import time
import copy
from datetime import datetime
from OneMinutesData import OneMinutesData
from CryptowatchDataGetter import CryptowatchDataGetter
from SystemFlg import SystemFlg


class MarketData2:
    @classmethod
    def initialize_from_bot_csv(cls, num_term, window_term, future_side_period, future_side_kijun):
        cls.num_term = num_term
        cls.window_term = window_term
        cls.max_term = num_term * window_term
        cls.future_side_period = future_side_period
        cls.future_side_kijun = future_side_kijun
        cls.ohlc_bot = OneMinutesData()
        cls.ohlc_bot.initialize()
        cls.ohlc_bot = cls.read_from_csv('one_min_data.csv')
        cls.ohlc_bot = cls.calc_ma2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_ma_kairi2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_momentum2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_rsi2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_future_side(cls.future_side_period, cls.future_side_kijun, cls.ohlc_bot)

    @classmethod
    def initialize_from_omd(cls, num_term, window_term, future_period, future_kijun, omd:OneMinutesData):
        cls.num_term = num_term
        cls.window_term = window_term
        cls.max_term = num_term * window_term
        cls.future_side_period = future_period
        cls.future_side_kijun = future_kijun
        cls.ohlc_bot = omd
        cls.ohlc_bot = cls.calc_ma2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_ma_kairi2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_momentum2(cls.ohlc_bot)
        cls.ohlc_bot = cls.calc_rsi2(cls.ohlc_bot)
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


    @classmethod
    def generate_df(cls, ohlc):
        end = len(ohlc.close) - cls.future_side_period
        df = pd.DataFrame()
        df = df.assign(dt=ohlc.dt[cls.max_term:end])
        df = df.assign(open=ohlc.open[cls.max_term:end])
        df = df.assign(high=ohlc.high[cls.max_term:end])
        df = df.assign(low=ohlc.low[cls.max_term:end])
        df = df.assign(close=ohlc.close[cls.max_term:end])
        df = df.assign(size=ohlc.size[cls.max_term:end])
        for k in ohlc.ma_kairi:
            col = 'ma_kairi' + str(k)
            df = df.assign(col=ohlc.ma_kairi[k][cls.max_term:end])
            df.rename(columns={'col': col}, inplace=True)
        for k in ohlc.rsi:
            col = 'rsi' + str(k)
            df = df.assign(col=ohlc.rsi[k][cls.max_term:end])
            df.rename(columns={'col': col}, inplace=True)
        for k in ohlc.momentum:
            col = 'mom' + str(k)
            df = df.assign(col=ohlc.momentum[k][cls.max_term:end])
            df.rename(columns={'col': col}, inplace=True)
        df = df.assign(future_side=ohlc.future_side[cls.max_term:])
        print('future side unique val')
        print(df['future_side'].value_counts(dropna=False, normalize=True))
        return df

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

    @classmethod
    def calc_future_side(cls, future_side_period, future_side_kijun, ohlc):
        for i in range(len(ohlc.close) - future_side_period):
            buy_max = 0
            sell_max = 0
            for j in range(i, i + future_side_period):
                buy_max = max(buy_max, ohlc.close[j] - ohlc.close[i])
                sell_max = max(sell_max, ohlc.close[i] - ohlc.close[j])
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
    def calc_ma2(cls, ohlc):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            ohlc.ma[term] = list(pd.Series(ohlc.close).rolling(window=term).mean())
        return ohlc

    @classmethod
    def update_ma2(cls):
        for i in range(cls.num_term):
            term =  (i+1) * cls.window_term
            close_con = cls.ohlc_bot.close[len(cls.ohlc_bot.close) - term - (len(cls.ohlc_bot.ma[term]) - len(cls.ohlc_bot.close) + 1):]
            updates = list(pd.Series(close_con).rolling(window=term).mean().dropna())
            cls.ohlc_bot.ma[term].extend(updates)

    @classmethod
    def calc_ma_kairi2(cls, ohlc):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            ohlc.ma_kairi[term] = list([x / y for (x,y) in zip(ohlc.close, ohlc.ma[term])])
        return ohlc

    @classmethod
    def update_ma_kairi2(cls):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            close_con = cls.ohlc_bot.close[len(cls.ohlc_bot.ma_kairi[term]) - len(cls.ohlc_bot.close):]
            ma_con = cls.ohlc_bot.ma[term][len(cls.ohlc_bot.ma_kairi[term]) - len(cls.ohlc_bot.ma[term]):]
            cls.ohlc_bot.ma_kairi[term].extend(list([x / y for (x, y) in zip(close_con, ma_con)]))

    @classmethod
    def calc_momentum2(cls, ohlc):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            ohlc.momentum[term] = list(pd.Series(ohlc.close).diff(term-1))
        return ohlc

    @classmethod
    def update_momentum2(cls):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
            close_con = cls.ohlc_bot.close[len(cls.ohlc_bot.close) - term - (len(cls.ohlc_bot.momentum[term]) - len(cls.ohlc_bot.close)+1)+1:]
            cls.ohlc_bot.momentum[term].extend(list(pd.Series(close_con).diff(term - 1).dropna()))

    @classmethod
    def calc_rsi2(cls, ohlc):
        for i in range(cls.num_term):
            term = (i+1) * cls.window_term
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
        for i in range(cls.max_term):
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
        for i in range(cls.max_term):
            term = i + 5
            kairi = []
            for j in range(len(cls.ohlc_bot.close) - len(cls.ohlc_bot.ma_kairi[term])):
                ind = len(cls.ohlc_bot.ma_kairi[term]) + j
                kairi.append(float(cls.ohlc_bot.close[ind]) / float(cls.ohlc_bot.ma[term][ind]))
            cls.ohlc_bot.ma_kairi[term].extend(kairi)

    @classmethod
    def update_momentum(cls):
        for i in range(cls.max_term):
            term = i + 5
            mom = []
            for j in range(len(cls.ohlc_bot.close) - len(cls.ohlc_bot.momentum[term])):
                mom.append(cls.ohlc_bot.close[len(cls.ohlc_bot.momentum[term] + j)] -
                           cls.ohlc_bot.close[len(cls.ohlc_bot.momentum[term] + j + term)])
            cls.ohlc_bot.momentum[term].extend(mom)

    @classmethod
    def update_rsi(cls):
        for i in range(cls.max_term):
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