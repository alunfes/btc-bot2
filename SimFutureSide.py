from MarketData import MarketData
from OneMinutesData import OneMinutesData
import numpy as np


class SimFutureSide:
    @classmethod
    def __initialize(cls):
        cls.pl = 0
        cls.pl_log = []
        cls.pl_std = 0
        cls.pl_per_min = 0
        cls.total_minus = 0
        cls.num_trade = 0
        cls.num_win = 0
        cls.win_rate = 0
        cls.entry_flg = ''
        cls.posi_side = ''
        cls.posi_price = 0
        cls.posi_size = 0
        cls.order_dt = None
        cls.order_price = 0

    @classmethod
    def __execute(cls, profit):
        cls.pl += profit
        cls.pl_log.append(cls.pl)
        cls.num_trade += 1
        if profit > 0:
            cls.num_win +=1
        cls.win_rate = float(cls.num_win) / float(cls.num_trade)
        cls.posi_side = ''
        cls.posi_price = 0
        cls.posi_size = 0
        cls.order_dt = None
        cls.entry_flg = ''
        cls.order_price = 0

    @classmethod
    def check_execution(cls, ind, side, order_price):
        if side == 'buy':
            if MarketData.ohlc_data.low[ind] <= order_price:
                return order_price
            else:
                return 0
        elif side == 'sell':
            if MarketData.ohlc_data.high[ind] >= order_price:
                return order_price
            else:
                return 0

    @classmethod
    def last_ind_operation(cls, ind):
        if cls.posi_side == 'buy':
            cls.__execute((MarketData.ohlc_data.close[ind] - cls.posi_price) * cls.posi_size)
        elif cls.posi_side == 'sell':
            cls.__execute((cls.posi_price - MarketData.ohlc_data.close[ind]) * cls.posi_size)
        cls.pl_std = np.array(cls.pl_log).std()
        cls.pl_per_min = cls.pl / float(len(cls.pl_log))
        for i,p in enumerate(cls.pl_log):
            if i>0:
                if cls.pl_log[i] - cls.pl_log[i-1] < 0:
                    cls.total_minus += cls.pl_log[i] - cls.pl_log[i-1]

    @classmethod
    def next_ind_operation(cls, ind):
        if cls.posi_side == 'buy':
            p = (MarketData.ohlc_data.close[ind] - cls.posi_price) * cls.posi_size
            cls.pl_log.append(cls.pl + p)
        elif cls.posi_side == 'sell':
            p = (cls.posi_price - MarketData.ohlc_data.close[ind]) * cls.posi_size
            cls.pl_log.append(cls.pl + p)
        else:
            if len(cls.pl_log) > 0:
                cls.pl_log.append(cls.pl_log[len(cls.pl_log)-1])
            else:
                cls.pl_log.append(0)

    @classmethod
    def check_matched_index(cls, test_x):
        key = 10
        test = list(test_x['ma_kairi'+str(key)])
        kairi = MarketData.ohlc_data.ma_kairi[key]
        for i in range(len(kairi)):
            flg = True
            for j in range(30):
                if test[j] != kairi[i+j]:
                    flg = False
                    break
            if flg:
                return i
        return -1

    @classmethod
    def sim(cls, test_x, predictions, pt):
        cls.__initialize()
        start = cls.check_matched_index(test_x)
        for i in range(len(predictions)-1):
            ind = i + start
            if cls.entry_flg == '':
                if predictions[i] == 2:
                    cls.entry_flg='sell'
                    cls.order_dt = MarketData.ohlc_data.dt[ind]
                    cls.order_price = MarketData.ohlc_data.close[ind]
                elif predictions[i] == 1:
                    cls.entry_flg = 'buy'
                    cls.order_dt = MarketData.ohlc_data.dt[ind]
                    cls.order_price = MarketData.ohlc_data.close[ind]
            elif cls.posi_side == '' and (cls.entry_flg == 'buy' or cls.entry_flg == 'sell'):
                exe_p = cls.check_execution(ind, cls.entry_flg, cls.order_price)
                if exe_p > 0:
                    cls.posi_price = exe_p
                    cls.posi_side = cls.entry_flg
                    cls.posi_size = 0.11
                    cls.order_dt = MarketData.ohlc_data.dt[ind]
                    cls.order_price = 0
                    cls.entry_flg = ''
                #in case prediction was changed before executed current order
                else:
                    if cls.entry_flg == 'buy' and predictions[i] == 2:
                        cls.entry_flg = 'sell'
                        cls.order_dt = MarketData.ohlc_data.dt[ind]
                        cls.order_price = MarketData.ohlc_data.close[ind]
                    elif cls.entry_flg == 'sell' and predictions[i] == 1:
                        cls.entry_flg = 'buy'
                        cls.order_dt = MarketData.ohlc_data.dt[ind]
                        cls.order_price = MarketData.ohlc_data.close[ind]
            elif cls.posi_side == 'buy' or cls.posi_side == 'sell':
                if (cls.posi_side == 'buy' and MarketData.ohlc_data.high[ind] >= pt + cls.posi_price) or \
                        (cls.posi_side == 'sell' and MarketData.ohlc_data.low[ind] <= cls.posi_price - pt): #pt
                    cls.__execute(cls.posi_size * pt)
                if cls.entry_flg == 'lc':
                    exe_p = cls.check_execution(ind, cls.posi_side, cls.order_price)
                    if exe_p > 0:
                        p = cls.order_price - cls.posi_price if cls.posi_side == 'buy' else cls.posi_price - cls.order_price
                        cls.__execute(cls.posi_size * p)
                if (cls.posi_side == 'buy' and predictions[i] == 2) or (cls.posi_side == 'sell' and predictions[i] == 1): #entry lc
                    cls.entry_flg = 'lc'
                    cls.order_dt = MarketData.ohlc_data.dt[ind]
                    #cls.order_price = MarketData.ohlc_data.close[ind]
                    cls.order_price = MarketData.ohlc_data.low[ind] if cls.posi_side == 'buy' else MarketData.ohlc_data.high[ind]
            cls.next_ind_operation(ind)
        cls.last_ind_operation(len(predictions)+start-1)
        return (cls.pl, cls.num_trade, cls.win_rate, cls.pl_log, cls.pl_std, cls.total_minus, cls.pl_per_min)

