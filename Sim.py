from MarketData2 import  MarketData2
from datetime import datetime


class Sim:
    @classmethod
    def initialize(cls, pl_kijun):
        cls.pl_kijun = pl_kijun
        cls.posi_initialize()
        cls.order_initailize()
        cls.pl = 0
        cls.holding_pl = 0
        cls.pl_log=[]
        cls.num_trade = 0
        cls.num_win = 0
        cls.win_rate = 0
        cls.margin_rate = 120.0
        cls.leverage = 15.0
        cls.initial_asset = 5000
        cls.asset = cls.initial_asset

    @classmethod
    def posi_initialize(cls):
        cls.posi_side = ''
        cls.posi_price = 0
        cls.posi_size = 0

    @classmethod
    def order_initailize(cls):
        cls.order_side = ''
        cls.order_id = ''
        cls.order_price = 0
        cls.order_size = 0
        cls.order_status = ''
        cls.order_dt = ''


    @classmethod
    def next_ind_operation(cls, ind):
        cls.check_execution(ind)
        cls.calc_asset(ind)
        cls.pl_log.append(cls.pl + cls.holding_pl)

    @classmethod
    def last_ind_operation(cls, ind):
        if cls.posi_side == 'buy':
            cls.calc_and_log_pl((MarketData2.ohlc_bot.close[ind] - cls.posi_price), cls.posi_size)
        elif cls.posi_side == 'sell':
            cls.calc_and_log_pl((cls.posi_price - MarketData2.ohlc_bot.close[ind]), cls.posi_size)

    @classmethod
    def calc_opt_size(cls, ind):
        return round((1.5 * cls.asset * cls.margin_rate) / MarketData2.ohlc_bot.close[ind] * 1.0/cls.leverage, 2)

    @classmethod
    def calc_and_log_pl(cls, ave_p, size):
        pl = (ave_p - cls.posi_price) * cls.posi_size if cls.posi_side == 'buy' else (cls.posi_price -ave_p) * cls.posi_size
        cls.pl += round(pl,2)
        cls.num_trade += 1
        if pl > 0:
            cls.num_win += 1
        cls.win_rate = round(float(cls.num_win) / float(cls.pl, cls.num_trade, cls.win_rate))

    @classmethod
    def calc_holding_pl(cls, ind):
        lastp = MarketData2.ohlc_bot.close[ind]
        cls.holding_pl = round((lastp - cls.posi_price) * cls.posi_size if cls.posi_side == 'buy' else (cls.posi_price - lastp) * cls.posi_size,2)

    @classmethod
    def calc_asset(cls, ind):
        cls.calc_hosting_pl(ind)
        cls.asset = cls.initial_asset + cls.pl + cls.holding_pl

    @classmethod
    def entry_order(cls, side, price, size, ind):
        cls.order_side = side
        cls.order_price = price
        cls.order_size = size
        cls.order_status = 'new boarding'
        cls.order_dt = MarketData2.ohlc_bot.dt[ind]

    @classmethod
    def pl_order(cls, ind):
        side = 'buy' if cls.posi_side == 'sell' else 'sell'
        price = cls.posi_price + cls.pl_kijun if cls.posi_side == 'buy' else cls.posi_price - cls.pl_kijun
        cls.order_side = side
        cls.order_price = price
        cls.order_size = cls.posi_size
        cls.order_status = 'pl ordering'
        cls.order_dt = MarketData2.ohlc_bot.dt[ind]

    @classmethod
    def check_execution(cls, ind):
        if cls.order_status == 'new boarding':
            cls.order_status = 'new boarded'
        elif cls.order_status == 'new boarded' or cls.order_status == 'cancelling order':
            if cls.order_side == 'buy':
                if MarketData2.ohlc_bot.low[ind] <= cls.order_price:
                    cls.posi_side = cls.order_side
                    cls.posi_price = cls.order_price
                    cls.posi_size = cls.order_size
                    cls.order_initailize()
                    return cls.order_price
                else:
                    if cls.order_status == 'cancelling order':
                        cls.order_initailize()
                    return 0
            elif cls.order_side == 'sell':
                if MarketData2.ohlc_bot.high[ind] >= cls.order_price:
                    cls.posi_side = cls.order_side
                    cls.posi_price = cls.order_price
                    cls.posi_size = cls.order_size
                    cls.order_initailize()
                    return cls.order_price
                else:
                    if cls.order_status == 'cancelling order':
                        cls.order_initailize()
                    return 0
        elif cls.order_status == 'pl ordering':
            if cls.order_side == 'buy':
                if MarketData2.ohlc_bot.low[ind] <= cls.order_price:
                    cls.calc_and_log_pl(cls.order_price, cls.order_size)
                    cls.order_initailize()
                    cls.posi_initialize()
                    return cls.order_price
                else:
                    return 0
            elif cls.order_side == 'sell':
                if MarketData2.ohlc_bot.high[ind] >= cls.order_price:
                    cls.calc_and_log_pl(cls.order_price, cls.order_size)
                    cls.order_initailize()
                    cls.posi_initialize()
                    return cls.order_price
                else:
                    return 0
        elif cls.order_status == 'tracing order':
            if cls.order_side == 'buy':
                if MarketData2.ohlc_bot.low[ind] <= cls.order_price:
                    cls.calc_and_log_pl(cls.order_price, cls.order_size)
                    cls.order_initailize()
                    cls.posi_initialize()
                    return cls.order_price
                else:
                    cls.order_price = MarketData2.ohlc_bot.close[ind]
                    return 0
            elif cls.order_side == 'sell':
                if MarketData2.ohlc_bot.high[ind] >= cls.order_price:
                    cls.calc_and_log_pl(cls.order_price, cls.order_size)
                    cls.order_initailize()
                    cls.posi_initialize()
                    return cls.order_price
                else:
                    cls.order_price = MarketData2.ohlc_bot.close[ind]
                    return 0

    @classmethod
    def exit_order(cls, ind):
        cls.order_side = 'buy' if cls.posi_side == 'sell' else 'sell'
        cls.order_price = MarketData2.ohlc_bot.close[ind]
        cls.order_size = cls.posi_size
        cls.order_status = 'tracing order'

    @classmethod
    def check_matched_index(cls, test_x):
        key = list(MarketData2.ohlc_bot.ma_kairi.keys())[0]
        test = list(test_x['ma_kairi'+str(key)])
        kairi = cls.data.ma_kairi[key]
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
    def start_sim(cls, test_x, prediction, pl_kijun, kairi_suspension_kijun, conservertive_trade = False):
        cls.initialize(pl_kijun)
        start_ind = cls.check_matched_index(test_x)
        for i in range(len(prediction) - 1):
            ind = i + start_ind
            if cls.posi_side == '' and cls.order_side == '' and abs(1.00 - MarketData2.ohlc_bot.ma_kairi[5][ind]) < kairi_suspension_kijun:
                if prediction[i] == 1:
                    cls.entry_order('buy', MarketData2.ohlc_bot.close[ind]+1, cls.calc_opt_size(ind), ind)
                elif prediction[i] == 2:
                    cls.entry_order('sell', MarketData2.ohlc_bot.close[ind]-1, cls.calc_opt_size(ind), ind)
            if conservertive_trade:
                # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。
                if (cls.posi_side == 'buy' and (prediction[i] == 2 or prediction[i] == 0 or prediction[i] == 3)) or \
                        (cls.posi_side=='sell' and (prediction[i] == 1 or prediction[i] == 0 or prediction[i] == 3)):
                    cls.exit_order(ind)
                    if cls.order_side !='':
                        cls.order_status = 'cancelling order'
                #ノーポジでオーダーが判定を逆の時にキャンセル。
                if (cls.order_side == 'buy' and cls.posi_side =='' and (prediction[i] == 2 or prediction[i] == 0 or prediction[i] == 3)) or (cls.order_side=='sell' and cls.posi_side =='' and (prediction[i] == 1 or prediction[i] == 0 or prediction[i] == 3)):
                    cls.order_status = 'cancelling order'
            elif conservertive_trade==False: #non conservertive trade
                # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。
                if (cls.posi_side == 'buy' and prediction[i] == 2) or \
                        (cls.posi_side == 'sell' and prediction[i] == 1):
                    cls.exit_order(ind)
                    if cls.order_side !='':
                        cls.order_status = 'cancelling order'
                #ノーポジでオーダーが判定を逆の時にキャンセル。
                if (cls.order_side == 'buy' and cls.posi_side=='' and prediction[i] == 2) or (
                        cls.order_side == 'sell' and cls.posi_side =='' and prediction[i] == 1):
                    cls.order_status = 'cancelling order'
            if abs(1.00 - MarketData2.ohlc_bot.ma_kairi[5][ind]) >= kairi_suspension_kijun: #kairiが一定以上の時
                if cls.posi_side != '':
                    cls.exit_order(ind)
            if cls.posi_side != '' and cls.order_side =='' and cls.order_status !='cancelling order':
                cls.pl_order(ind)
            cls.next_ind_operation(ind)
        cls.last_ind_operation(len(prediction)+start_ind-1)
        return (cls.pl, cls.num_trade, cls.win_rate, cls.pl_log)


