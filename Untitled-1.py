
#%%
get_ipython().system('pip install catboost')
get_ipython().system('pip install optuna')


#%%
from google.colab import drive
drive.mount('/content/drive')


#%%
get_ipython().system("ls '/content/drive/My Drive/' -a")


#%%
import pandas as pd
import threading

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

    def cut_data(self, num_data):
        self.unix_time = self.unix_time[len(self.unix_time) - num_data:]
        self.dt = self.dt[len(self.dt) - num_data:]
        self.open = self.open[len(self.open) - num_data:]
        self.high = self.high[len(self.high) - num_data:]
        self.low = self.low[len(self.low) - num_data:]
        self.close = self.close[len(self.close) - num_data:]
        self.size = self.size[len(self.size) - num_data:]
        for k in self.ma:
            self.ma[k] = self.ma[k][len(self.ma[k])-num_data:]
        for k in self.ma_kairi:
            self.ma_kairi[k] = self.ma_kairi[k][len(self.ma_kairi[k])-num_data:]
        for k in self.momentum:
            self.momentum[k] = self.momentum[k][len(self.momentum[k])-num_data:]
        for k in self.rsi:
            self.rsi[k] = self.rsi[k][len(self.rsi[k])-num_data:]
        self.future_side = self.future_side[len(self.future_side) - num_data:]

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
        


class SystemFlg:
    @classmethod
    def initialize(cls):
        cls.system_flg = True
        cls.lock = threading.Lock()

    @classmethod
    def set_system_flg(cls, flg):
        with cls.lock:
            cls.system_flg = flg

    @classmethod
    def get_system_flg(cls):
        return cls.system_flg
    
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
        cls.ohlc_bot = cls.read_from_csv('/content/drive/My Drive/one_min_data.csv')
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
            if term > 1:
                ohlc.ma[term] = list(pd.Series(ohlc.close).rolling(window=term).mean())
        return ohlc

    @classmethod
    def update_ma2(cls):
        for i in range(cls.num_term):
            term =  (i+1) * cls.window_term
            if term > 1:
                close_con = cls.ohlc_bot.close[len(cls.ohlc_bot.close) - term - (len(cls.ohlc_bot.ma[term]) - len(cls.ohlc_bot.close) + 1):]
                updates = list(pd.Series(close_con).rolling(window=term).mean().dropna())
                cls.ohlc_bot.ma[term].extend(updates)

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

class Account:
    def __init__(self):
        self.realized_pl = 0
        self.unrealized_pl = 0
        self.total_pl = 0
        self.num_trade = 0
        self.num_win = 0
        self.win_rate = 0
        self.total_min = 0
        self.pl_per_min = 0
        self.ave_pl = 0

        self.__initialize_unexe_data()
        self.__initialize_cancel_all_orders()
        self.__initialize_holding_data()

        self.price_tracing_order_target_size = 0
        self.price_tracing_order_side = ''
        self.price_tracing_order_dt = ''
        self.price_tracing_order_i = 0
        self.price_tracing_order_flg = False

        self.margin_rate = 120.0
        self.leverage = 15.0

        self.realized_pl_log = {}
        self.total_pl_log = {}
        self.holding_side_log = {}
        self.ave_holding_price_log = {}
        self.ave_holding_size_log = {}
        self.action_log = {}
        self.i_log = []
        self.ind_log = []
        self.prediction_log = {}
        self.initial_asset = 5000
        self.asset = self.initial_asset
        self.action_log_num = 0

    def __initialize_unexe_data(self):
        self.unexe_price = {}
        self.unexe_size = {}
        self.unexe_side = {}
        self.unexe_i = {}
        self.unexe_dt = {}
        self.unexe_cancel = {}
        self.unexe_info = {}


    def __initialize_cancel_all_orders(self):
        self.cancel_all_orders_flg = False
        self.cancel_all_order_i = 0

    def __initialize_holding_data(self):
        self.ave_holding_price = 0
        self.ave_holding_size = 0
        self.last_entry_time = ''
        self.last_entry_i = 0
        self.holding_side = ''

    def __remove_unexe_key(self, unexe_key):
        self.unexe_price.pop(unexe_key)
        self.unexe_size.pop(unexe_key)
        self.unexe_side.pop(unexe_key)
        self.unexe_i.pop(unexe_key)
        self.unexe_dt.pop(unexe_key)
        self.unexe_cancel.pop(unexe_key)
        self.unexe_info.pop(unexe_key)

    def move_to_next(self, prediction, ind, i):
        self.__check_execution(prediction, ind, i)
        self.__check_cancel(ind, i)
        self.__calc_unrealized_pl(ind)
        self.realized_pl_log[i] = self.realized_pl
        self.total_pl = self.realized_pl + self.unrealized_pl
        self.total_pl_log[i] = self.total_pl
        self.asset = self.initial_asset + self.total_pl
        self.holding_side_log[i] = self.holding_side
        self.ave_holding_size_log[i] = self.ave_holding_size
        self.ave_holding_price_log[i] = self.ave_holding_price
        self.action_log_num = 0
        self.total_min += 1
        self.i_log.append(i)
        self.ind_log.append(ind)
        self.prediction_log[i] = prediction

    def last_day_operation(self, ind, i):
        self.__check_execution(0, ind, i)
        self.__check_cancel(ind,i)
        self.__calc_unrealized_pl(ind)
        self.realized_pl_log[i] = self.realized_pl
        self.total_pl = self.realized_pl + self.unrealized_pl
        self.total_pl_log[i] = self.total_pl
        self.asset = self.initial_asset + self.total_pl
        self.holding_side_log[i] = self.holding_side
        self.ave_holding_size_log[i] = self.ave_holding_size
        self.ave_holding_price_log[i] = self.ave_holding_price
        self.win_rate = self.num_win / float(self.num_trade)
        self.pl_per_min = self.total_pl / float(self.total_min)
        self.i_log.append(i)
        self.ind_log.append(ind)
        self.prediction_log[i] = 0

    def calc_opt_size(self, ind):
        return round((self.asset * self.margin_rate) / MarketData2.ohlc_bot.close[ind] * 1.0/self.leverage, 2)

    def __add_action_log(self, log, i):
        self.action_log[str(i)+'-'+str(self.action_log_num)] = log
        self.action_log_num += 1
        self.i_log.append(i)

    def __calc_unrealized_pl(self, ind):
        lastp = MarketData2.ohlc_bot.close[ind]
        self.unrealized_pl = round((lastp - self.ave_holding_price) * self.ave_holding_size if self.holding_side ==     'buy' else (self.ave_holding_price - lastp) * self.ave_holding_size,2)

    def entry_order(self, side, price, size, info, ind, i):
        if self.cancel_all_orders_flg == False:
            n = len(self.unexe_side)
            self.unexe_side[n] = side
            self.unexe_price[n] = price
            self.unexe_size[n] = size
            self.unexe_dt[n] = MarketData2.ohlc_bot.dt[ind]
            self.unexe_i[n] = i
            self.unexe_cancel[n] = False
            self.unexe_info[n] = info
            self.__add_action_log("Entry Order for " + side + " @" + str(price) + " x " + str(size),i)
            #print('entry, '+side+' @'+str(price)+' x'+str(size)+' n='+str(n))

    def __force_entry(self, prediction, unexe_key, ind, i):
        price = self.unexe_price[unexe_key]
        self.__remove_unexe_key(unexe_key)
        if prediction == 1 or prediction == 2:
            n = len(self.unexe_side)
            self.unexe_side[n] = 'buy' if prediction == 1 else 'sell'
            self.unexe_price[n] = price
            self.unexe_size[n] = self.calc_opt_size(ind)
            self.unexe_dt[n] = MarketData2.ohlc_bot.dt[ind]
            self.unexe_i[n] = i
            self.unexe_cancel[n] = False
            self.unexe_info[n] = 'entry after pl execution'
            self.__add_action_log('Force entry after pl execution',i)
            self.__execute(n, prediction, ind, i)
            #print('force entry, '+self.unexe_side[n]+' @'+str(price)+' j='+str(j))

    def exit_all_positions(self, ind, i):
        if 'exit all' not in list(self.unexe_info.values()):
            side = 'buy' if self.holding_side == 'sell' else 'sell'
            price = round((MarketData2.ohlc_bot.open[ind+1] + MarketData2.ohlc_bot.close[ind+1]) * 0.5)
            self.entry_order(side, price, self.ave_holding_size,'exit all',ind,i)
            self.__add_action_log("Exit all",i)
            #print('exit all order, '+side)

    def pl_order(self, pl_kijun, ind, i):
        side = 'buy' if self.holding_side == 'sell' else 'sell'
        price = self.ave_holding_price + pl_kijun if self.holding_side == 'buy' else self.ave_holding_price - pl_kijun
        self.entry_order(side, price, self.ave_holding_size, 'pl order', ind, i)
        self.__add_action_log("Entry PL Order" + side + " @" + str(price) + " x " + str(self.ave_holding_size),i)
        #print('pl order, '+side)

    def cancel_all_orders(self, ind, i):
        if len(self.unexe_side) > 0 and self.cancel_all_orders_flg == False:
            self.cancel_all_orders_flg = True
            self.cancel_all_order_i = i
            self.__add_action_log("Cancelling All Orders",i)
            #print('cancel all order,')

    def cancel_order(self, unexe_key, ind, i):
        if self.unexe_cancel[unexe_key] == False:
            self.unexe_cancel[unexe_key] = True
            self.unexe_i[unexe_key] = i
            self.__add_action_log("Cancelling order #" + str(unexe_key),i)
            #print('cancel order, '+'key ='+str(unexe_key))

    def __check_cancel(self, ind, i):
        if self.cancel_all_orders_flg:
            if self.cancel_all_order_i < i:
                self.__execute_cancel_all_orders(i)
        else:
            cancelled_index = ''
            for j in list(self.unexe_cancel.keys())[:]:
                if self.unexe_cancel[j] and self.unexe_i[j] < i:
                    self.__remove_unexe_key(j)
                    cancelled_index += str(j) + ','
            if cancelled_index != '':
                  self.__add_action_log("Cancelled orders #" + cancelled_index,i)
                  #print('cancelled orders')

    def __execute_cancel(self, ind, i, unexe_key):
        self.__remove_unexe_key(unexe_key)
        self.__add_action_log("Cancelled order #" + str(unexe_key), i)
        print('execited cancel')

    def __execute_cancel_all_orders(self,i):
        for j in list(self.unexe_info.keys())[:]:
            if self.unexe_info[j] != 'exit all':
                self.__remove_unexe_key(j)
        self.__initialize_cancel_all_orders()
        self.__add_action_log("Cancelled all orders",i)
        #print('execited cancel all')

    def __check_execution(self, prediction, ind, i):
        for j in list(self.unexe_side.keys())[:]:
            #print(self.unexe_side)
            #print(self.unexe_i)
            if self.unexe_i[j] < i:
                if self.unexe_side[j] == 'buy' and MarketData2.ohlc_bot.low[ind] <= self.unexe_price[j]:
                    self.__execute(j, prediction, ind, i)
                  #print('executed')
                elif self.unexe_side[j] == 'sell' and MarketData2.ohlc_bot.high[ind] >= self.unexe_price[j]:
                    self.__execute(j, prediction, ind, i)
                    #print('executed')

    def __execute(self, unexe_key, prediction, ind, i):
        if self.holding_side =='':
            self.holding_side = self.unexe_side[unexe_key]
            self.ave_holding_size = self.unexe_size[unexe_key]
            self.ave_holding_price = self.unexe_price[unexe_key]
            self.last_entry_i = i
            self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
        elif self.holding_side == 'buy':
            if self.unexe_side[unexe_key] == 'buy':
                self.ave_holding_size += self.unexe_size[unexe_key]
                self.ave_holding_price = ((self.ave_holding_price * self.ave_holding_size) + (self.unexe_price[unexe_key] * self.unexe_size[unexe_key])) / (self.ave_holding_size + self.unexe_size[unexe_key])
                self.last_entry_i = i
                self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
            elif self.unexe_side[unexe_key] == 'sell':
                if self.unexe_size[unexe_key] < self.ave_holding_size:
                    self.ave_holding_size -= self.unexe_size[unexe_key]
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                elif self.unexe_size[unexe_key] > self.ave_holding_size:
                    self.ave_holding_size = self.unexe_size[unexe_key] - self.ave_holding_size
                    self.ave_holding_price = self.unexe_size[unexe_key]
                    self.holding_side = 'sell'
                    self.last_entry_i = i
                    self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                elif self.unexe_size[unexe_key] == self.ave_holding_size:
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                    self.__initialize_holding_data()
        elif self.holding_side == 'sell':
            if self.unexe_side[unexe_key] == 'sell':
                self.ave_holding_size += self.unexe_size[unexe_key]
                self.ave_holding_price = ((self.ave_holding_price * self.ave_holding_size) + (self.unexe_price[unexe_key] * self.unexe_size[unexe_key])) / (self.ave_holding_size + self.unexe_size[unexe_key])
                self.last_entry_i = i
                self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
            elif self.unexe_side[unexe_key] == 'buy':
                if self.unexe_size[unexe_key] < self.ave_holding_size:
                    self.ave_holding_size -= self.unexe_size[unexe_key]
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                elif self.unexe_size[unexe_key] > self.ave_holding_size:
                    self.ave_holding_size = self.unexe_size[unexe_key] - self.ave_holding_size
                    self.ave_holding_price = self.unexe_size[unexe_key]
                    self.holding_side = 'buy'
                    self.last_entry_i = i
                    self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                elif self.unexe_size[unexe_key] == self.ave_holding_size:
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                    self.__initialize_holding_data()
        if self.unexe_info[unexe_key] == 'pl order':
            self.__force_entry(prediction, unexe_key, ind, i)
        else:
            self.__add_action_log("Executed " + self.unexe_side[unexe_key] + " @" + str(self.unexe_price[unexe_key]) + " x " + str(self.unexe_size[unexe_key]),i)
            self.__remove_unexe_key(unexe_key)

    def __update_cum_pl(self, ind, i, unexe_key, price, size):
        pl = 0
        if self.holding_side == 'buy':
            if self.unexe_side[unexe_key] == 'sell':
                pl = (price - self.ave_holding_price) * size
        elif self.holding_side == 'sell':
            if self.unexe_side[unexe_key] == 'buy':
                pl = (self.ave_holding_price - price) * size
        self.num_trade += 1
        if pl > 0:
            self.num_win += 1
        self.realized_pl += pl
        
        
from datetime import datetime


class Sim:
    @classmethod
    def check_matched_index(cls, test_x):
        key = list(cls.ohlc.ma_kairi.keys())[0]
        test = list(test_x['ma_kairi'+str(key)])
        kairi = cls.ohlc.ma_kairi[key]
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
    def start_sim(cls, test_x, prediction, pl_kijun, kairi_suspension_kijun, conservertive_trade, ohlc):
        cls.ac = Account()
        cls.ohlc = ohlc
        start_ind = cls.check_matched_index(test_x)
        for i in range(len(prediction) - 1):
            ind = i + start_ind
            if cls.ac.holding_side == '' and len(cls.ac.unexe_side) == 0 and abs(1.00 - ohlc.ma_kairi[list(ohlc.ma_kairi.keys())[-1]][ind]) < kairi_suspension_kijun:
                if prediction[i] == 1:
                    cls.ac.entry_order('buy', cls.ohlc.close[ind], cls.ac.calc_opt_size(ind),'new entry', ind, i)
                elif prediction[i] == 2:
                    cls.ac.entry_order('sell',cls.ohlc.close[ind], cls.ac.calc_opt_size(ind), 'new entry',ind, i)
            if conservertive_trade:
                # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。
                if (cls.ac.holding_side == 'buy' and (prediction[i] == 2 or prediction[i] == 0 or prediction[i] == 3)) or                         (cls.ac.holding_side=='sell' and (prediction[i] == 1 or prediction[i] == 0 or prediction[i] == 3)):
                    cls.ac.cancel_all_orders(ind,i)
                    if cls.ac.holding_side !='' :
                        cls.ac.exit_all_positions(ind,i)
                #ノーポジでオーダーが判定を逆の時にキャンセル。
                if cls.ac.holding_side =='':
                    for j in list(cls.ac.unexe_side.keys())[:]:
                        if (cls.ac.unexe_side[j] == 'buy' and (prediction[i] == 2 or prediction[i] == 0 or prediction[i] == 3)) or  (cls.ac.unexe_side[j]=='sell' and (prediction[i] == 1 or prediction[i] == 0 or prediction[i] == 3)):
                            cls.ac.cancel_order(j,ind,i)
            elif conservertive_trade==False: #non conservertive trade
                # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。
                if (cls.ac.holding_side == 'buy' and prediction[i] == 2) or                         (cls.ac.holding_side == 'sell' and prediction[i] == 1):
                    cls.ac.cancel_all_orders(ind,i)
                    if cls.ac.holding_side !='' :
                        cls.ac.exit_all_positions(ind,i)
                #ノーポジでオーダーが判定を逆の時にキャンセル。
                if cls.ac.holding_side =='':
                    for j in list(cls.ac.unexe_side.keys())[:]:
                        if (cls.ac.unexe_side[j]  == 'buy' and cls.ac.holding_side=='' and prediction[i] == 2) or (
                                cls.ac.unexe_side[j] == 'sell' and cls.ac.holding_side =='' and prediction[i] == 1):
                            cls.ac.cancel_order(j,ind,i)
            if abs(1.00 - ohlc.ma_kairi[list(ohlc.ma_kairi.keys())[-1]][ind]) >= kairi_suspension_kijun: #kairiが一定以上の時
                if len(cls.ac.unexe_side) > 0:
                    cls.ac.cancel_all_orders(ind,i)
            if cls.ac.holding_side != '' and len(cls.ac.unexe_side) == 0 and cls.ac.cancel_all_orders_flg == False:
                cls.ac.pl_order(pl_kijun,ind,i)
            cls.ac.move_to_next(prediction[i],ind,i)
        cls.ac.last_day_operation(len(prediction)+start_ind-1,len(prediction) - 1)
        return (cls.ac.total_pl, cls.ac.num_trade, cls.ac.win_rate, cls.ac.total_pl_log)




#%%
import catboost as cb
from catboost import Pool
from numba import jit
import numpy as np
import pandas as pd


class CatboostModel:
    @jit
    def generate_data(self, df:pd.DataFrame, test_size=0.2):
        df['future_side'] = df['future_side'].map({'no':0, 'buy':1, 'sell':2, 'both':3}).astype(int)
        df = df.drop(['dt','open','high','low','close','size'],axis = 1)
        size = int(round(df['future_side'].count() * (1-test_size)))
        train_x = df.drop('future_side',axis=1).iloc[0:size]
        train_y = df['future_side'].iloc[0:size]
        test_x = df.drop('future_side',axis=1).iloc[size:]
        test_y = df['future_side'].iloc[size:]
        return train_x, test_x, train_y, test_y
    
    @jit
    def train(self, train_x, train_y):
        train_pool = Pool(train_x, label=train_y)
        model = cb.CatBoostClassifier(loss_function='MultiClass', num_boost_round=500000, learning_rate=0.001, 
                                      #random_strength=100, 
                                      depth=4,
                                      #bagging_temperature=0.02, 
                                      task_type='GPU', verbose=50000)
        clf = model.fit(train_pool)
        return clf

    @jit
    def calc_accuracy(self, predict, test_y):
        num = len(predict)
        matched = 0
        y = np.array(test_y)
        for i in range(len(predict)):
            if predict[i] == y[i]:
                matched += 1
        return float(matched) / float(num)


#%%
import sklearn.metrics
from functools import partial
import optuna


class Optuning:
    def objective(trial):
        future_period = trial.suggest_int('future_period', 5, 500)
        future_kijun = trial.suggest_int('future_kijun', 100, 10000)
        MarketData.initialize_from_bot_csv(110, future_period, future_kijun)
        df = MarketData.generate_df(MarketData.ohlc_bot)
        model  =CatboostModel()
        train_x, test_x, train_y, test_y = model.generate_data(df,0.0)
        
        ave_pl = 0
        window = 700
        train_length = 10000
        test_length = 1500
        
        params={'task_type': 'GPU','verbose': False,'loss_function':'MultiClass'}
        params['num_boost_round'] = trial.suggest_int('num_boost_round', 1000, 30000)
       # params['iterations'] = trial.suggest_int('iterations', 50, 300)
        params['depth'] = trial.suggest_int('depth', 4, 10)
        params['learning_rate'] = trial.suggest_loguniform('learning_rate', 0.001, 0.3)
        params['random_strength'] =trial.suggest_int('random_strength', 0, 100)
        params['bagging_temperature'] = trial.suggest_loguniform('bagging_temperature', 0.01, 100.00)
        '''
        params = {#'num_boost_round': trial.suggest_int('num_boost_round', 1000, 30000), 
                  'iterations' : trial.suggest_int('iterations', 50, 300),
                  'depth' : trial.suggest_int('depth', 4, 10),
           'learning_rate' : trial.suggest_loguniform('learning_rate', 0.001, 0.3),
                  'random_strength' :trial.suggest_int('random_strength', 0, 100),
                  'bagging_temperature' :trial.suggest_loguniform('bagging_temperature', 0.01, 100.00),
                  #'task_type': 'GPU',
                  #'verbose': False
        }
        #'od_type': trial.suggest_categorical('od_type', ['IncToDec', 'Iter']),
        #'od_wait' :trial.suggest_int('od_wait', 10, 50),
        #'early_stopping_rounds': 10,
        '''
        

        for i in range(20):
            pre_train_x = train_x.iloc[len(train_x)-train_length:]
            pre_train_y = train_y.iloc[len(train_y)-train_length:]
            
            pre_train_x = train_x.iloc[i*window:(i*window)+train_length]
            pre_train_y = train_y.iloc[i*window:(i*window)+train_length]
            pre_test_x = train_x.iloc[(i*window)+train_length:(i*window)+train_length + test_length]
            pre_test_y = train_y.iloc[(i*window)+train_length:(i*window)+train_length + test_length]
            
            train_pool = Pool(pre_train_x, label=pre_train_y)
            test_pool = Pool(pre_test_x)
            cbc= cb.CatBoostClassifier(**params)
            clf = cbc.fit(train_pool)
            preds = clf.predict(test_pool)
            res = SimFutureSide.sim(pre_test_x, preds, future_kijun, MarketData.ohlc_bot)
            ave_pl += res[0]
            print('i={},pl={}'.format(i,res[0]))
        return -1.0 * float(ave_pl) / 10.0
    
    def convert_data_for_optuna(train_x, train_y, test_size = 0.2):
        size = int((1- test_size) * len(train_y))
        pre_train_y = train_y.iloc[0:size]
        pre_test_y = train_y.iloc[size:]
        pre_train_x = train_x.iloc[0:size]
        pre_test_x = train_x.iloc[size:]
        return pre_train_x, pre_train_y, pre_test_x, pre_test_y


#%%
import matplotlib.pyplot as plt
import time
import copy
import pickle
from catboost import Pool

num_term = 100
window_term = 1
kijun = 500
kairi_suspension_kijun = 1.001
conservertive_trade = False
period = 30

MarketData2.initialize_from_bot_csv(num_term,window_term, period, kijun)
df = MarketData2.generate_df(MarketData2.ohlc_bot)
model = CatboostModel()
train_x, test_x, train_y, test_y = model.generate_data(df,0.05)
train_xx = train_x
train_yy = train_y
test_xx = test_x
test_yy = test_y
#train_xx = train_x.iloc[n:30000 + n]
#train_yy = train_y.iloc[n:30000 + n]
#test_xx = train_x.iloc[30000 + n:32000 + n]
#test_yy = train_y.iloc[30000 + n:32000 + n]
start = time.time()
cbm = model.train(train_xx, train_yy)
pickle.dump(cbm, open('/content/drive/My Drive/Model/cat_model.dat', 'wb'))
prediction = cbm.predict(Pool(train_xx))
elapsed_time = time.time() - start
print("elapsed_time:{0}".format(elapsed_time/60) + "[min]")
print('train accuracy={}'.format(model.calc_accuracy(prediction, train_yy)))
if len(test_xx) > 0:
    prediction = cbm.predict(Pool(test_xx))
    print('test accuracy={}'.format(model.calc_accuracy(prediction, test_yy)))
    res = Sim.start_sim(test_xx, prediction, kijun, kairi_suspension_kijun, conservertive_trade, MarketData2.ohlc_bot)
    print('pl={},num={},win_rate={}'.format(res[0],res[1],res[2]))
    plt.plot(list(res[3].values()), label="pl")
    plt.show()


#%%
prediction = cbm.predict(Pool(test_xx))
print('test accuracy={}'.format(model.calc_accuracy(prediction, test_yy)))
res = Sim.start_sim(test_xx, prediction, kijun, kairi_suspension_kijun, conservertive_trade, MarketData2.ohlc_bot)
print('pl={},num={},win_rate={}'.format(res[0],res[1],res[2]))
plt.plot(list(res[3].values()), label="pl")
plt.show()


#%%
import matplotlib.pyplot as plt
import time
import copy
import pickle
from catboost import Pool

num_term = 100
window_term = 1
kijun = 500
kairi_suspension_kijun = 1.001
conservertive_trade = False
period = 30
res_list= []

for i in range(10):
    print(str(i)+':')
    MarketData2.initialize_from_bot_csv(num_term,window_term, period, kijun)
    df = MarketData2.generate_df(MarketData2.ohlc_bot)
    model = CatboostModel()
    train_x, test_x, train_y, test_y = model.generate_data(df,0.0)
    #train_xx = train_x
    #train_yy = train_y
    #test_xx = test_x
    #test_yy = test_y
    n = i * 1000
    train_xx = train_x.iloc[n:30000 + n]
    train_yy = train_y.iloc[n:30000 + n]
    test_xx = train_x.iloc[30000 + n:32000 + n]
    test_yy = train_y.iloc[30000 + n:32000 + n]
    start = time.time()
    cbm = model.train(train_xx, train_yy)
    pickle.dump(cbm, open('/content/drive/My Drive/Model/cat_model.dat', 'wb'))
    prediction = cbm.predict(Pool(train_xx))
    elapsed_time = time.time() - start
    print("elapsed_time:{0}".format(elapsed_time/60) + "[min]")
    print('train accuracy={}'.format(model.calc_accuracy(prediction, train_yy)))
    if len(test_xx) > 0:
        prediction = cbm.predict(Pool(test_xx))
        print('test accuracy={}'.format(model.calc_accuracy(prediction, test_yy)))
        res = Sim.start_sim(test_xx, prediction, kijun, kairi_suspension_kijun, conservertive_trade, MarketData2.ohlc_bot)
        res_list.append(res)
        print('pl={},num={},win_rate={}'.format(res[0],res[1],res[2]))
        plt.plot(list(res[3].values()), label="pl")
        plt.show()
        
for r in res_list:
    print(r[0])


#%%
kijun = 500
kairi_suspension_kijun = 1.005
conservertive_trade = False
prediction = cbm.predict(Pool(train_xx))
res = Sim.start_sim(train_xx, prediction, kijun, kairi_suspension_kijun, conservertive_trade, MarketData2.ohlc_bot)
print('pl={},num={},win_rate={}'.format(res[0],res[1],res[2]))
plt.plot(list(res[3].values()), label="pl")
plt.show()


#%%
MarketData2.initialize_from_bot_csv(100,1, 30, 500)


#%%
plt.plot(MarketData2.ohlc_bot.close, label="pl")
plt.show()


#%%
import sklearn.metrics
from functools import partial
import optuna


class Optuning:
    def objective(trial):
        future_period = trial.suggest_int('future_period', 5, 500)
        future_kijun = trial.suggest_int('future_kijun', 100, 10000)
        MarketData.initialize_from_bot_csv(110, future_period, future_kijun)
        df = MarketData.generate_df(MarketData.ohlc_bot)
        model  =CatboostModel()
        train_x, test_x, train_y, test_y = model.generate_data(df,0.0)
        
        ave_pl = 0
        window = 700
        train_length = 10000
        test_length = 1500
        
        params={'task_type': 'GPU','verbose': False,'loss_function':'MultiClass'}
        params['num_boost_round'] = trial.suggest_int('num_boost_round', 1000, 30000)
       # params['iterations'] = trial.suggest_int('iterations', 50, 300)
        params['depth'] = trial.suggest_int('depth', 4, 10)
        params['learning_rate'] = trial.suggest_loguniform('learning_rate', 0.001, 0.3)
        params['random_strength'] =trial.suggest_int('random_strength', 0, 100)
        params['bagging_temperature'] = trial.suggest_loguniform('bagging_temperature', 0.01, 100.00)
        '''
        params = {#'num_boost_round': trial.suggest_int('num_boost_round', 1000, 30000), 
                  'iterations' : trial.suggest_int('iterations', 50, 300),
                  'depth' : trial.suggest_int('depth', 4, 10),
           'learning_rate' : trial.suggest_loguniform('learning_rate', 0.001, 0.3),
                  'random_strength' :trial.suggest_int('random_strength', 0, 100),
                  'bagging_temperature' :trial.suggest_loguniform('bagging_temperature', 0.01, 100.00),
                  #'task_type': 'GPU',
                  #'verbose': False
        }
        #'od_type': trial.suggest_categorical('od_type', ['IncToDec', 'Iter']),
        #'od_wait' :trial.suggest_int('od_wait', 10, 50),
        #'early_stopping_rounds': 10,
        '''
        

        for i in range(20):
            pre_train_x = train_x.iloc[len(train_x)-train_length:]
            pre_train_y = train_y.iloc[len(train_y)-train_length:]
            
            pre_train_x = train_x.iloc[i*window:(i*window)+train_length]
            pre_train_y = train_y.iloc[i*window:(i*window)+train_length]
            pre_test_x = train_x.iloc[(i*window)+train_length:(i*window)+train_length + test_length]
            pre_test_y = train_y.iloc[(i*window)+train_length:(i*window)+train_length + test_length]
            
            train_pool = Pool(pre_train_x, label=pre_train_y)
            test_pool = Pool(pre_test_x)
            cbc= cb.CatBoostClassifier(**params)
            clf = cbc.fit(train_pool)
            preds = clf.predict(test_pool)
            res = SimFutureSide.sim(pre_test_x, preds, future_kijun, MarketData.ohlc_bot)
            ave_pl += res[0]
            print('i={},pl={}'.format(i,res[0]))
        return -1.0 * float(ave_pl) / 10.0
    
    def convert_data_for_optuna(train_x, train_y, test_size = 0.2):
        size = int((1- test_size) * len(train_y))
        pre_train_y = train_y.iloc[0:size]
        pre_test_y = train_y.iloc[size:]
        pre_train_x = train_x.iloc[0:size]
        pre_test_x = train_x.iloc[size:]
        return pre_train_x, pre_train_y, pre_test_x, pre_test_y


#%%
study = optuna.create_study()
study.optimize(Optuning.objective, n_trials=30)


#%%
import matplotlib.pyplot as plt
import time
import pickle
from catboost import Pool

start = time.time()
MarketData.initialize_from_bot_csv(110, 100, 900)
df = MarketData.generate_df(MarketData.ohlc_bot)
model = CatboostModel()
train_x, test_x, train_y, test_y = model.generate_data(df,0.1)
#train_x = train_x.iloc[len(train_x)-10000:]
#train_y = train_y.iloc[len(train_y)-10000:]
params = {'num_boost_round': 1000,'loss_function':'MultiClass',
                 'task_type': 'GPU','verbose': False}
cbc = cb.CatBoostClassifier(**params)
clf = cbc.fit(train_x, train_y)
pickle.dump(clf, open('/content/drive/My Drive/cat_model.dat', 'wb'))
prediction = clf.predict(Pool(train_x))
elapsed_time = time.time() - start
print("elapsed_time:{0}".format(elapsed_time/60) + "[min]")
print('train accuracy={}'.format(model.calc_accuracy(prediction, train_y)))
prediction = clf.predict(Pool(test_x))
print('test accuracy={}'.format(model.calc_accuracy(prediction, test_y)))

res = SimFutureSide.sim(test_x, prediction, 900, MarketData.ohlc_bot)
print('pl={},num={},win_rate={}'.format(res[0],res[1],res[2]))
plt.plot(res[3], label="pl")
plt.show()


#%%
plt.plot(MarketData.ohlc_bot.close, label="close")
plt.show()


#%%
list(MarketData.ohlc_bot.ma_kairi.keys())[0]


#%%



