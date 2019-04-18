from MarketData2 import  MarketData2


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


    def __initialize_cancel_all_orders(self):
        self.cancel_all_orders_flg = False
        self.cancel_all_order_i = 0

    def __initialize_holding_data(self):
        self.ave_holding_price = 0
        self.ave_holding_size = 0
        self.last_entry_time = ''
        self.last_entry_i = 0
        self.holding_side = ''

    def __remove_unexe_ind(self, unexe_ind):
        self.unexe_price.pop(unexe_ind)
        self.unexe_size.pop(unexe_ind)
        self.unexe_side.pop(unexe_ind)
        self.unexe_i.pop(unexe_ind)
        self.unexe_dt.pop(unexe_ind)
        self.unexe_cancel.pop(unexe_ind)

    def move_to_next(self, ind, i):
        self.__check_execution(ind, i)
        self.__check_cancel(ind, i)
        self.__calc_unrealized_pl(ind)
        self.realized_pl_log[i] = self.realized_pl
        self.total_pl = self.realized_pl + self.unrealized_pl
        self.total_pl_log[i] = self.total_pl
        self.holding_side_log[i] = self.holding_side
        self.ave_holding_size_log[i] = self.ave_holding_size
        self.ave_holding_price_log[i] = self.ave_holding_price
        self.action_log_num = 0
        self.total_min += 1

    def last_day_operation(self, ind, i):
        self.__check_execution(ind, i)
        self.__check_cancel(ind,i)
        self.__calc_unrealized_pl(ind)
        self.realized_pl_log[i] = self.realized_pl
        self.total_pl = self.realized_pl + self.unrealized_pl
        self.total_pl_log[i] = self.total_pl
        self.holding_side_log[i] = self.holding_side
        self.ave_holding_size_log[i] = self.ave_holding_size
        self.ave_holding_price_log[i] = self.ave_holding_price
        self.win_rate = self.num_win / float(self.num_trade)
        self.pl_per_min = self.total_pl / float(self.total_min)

    def calc_opt_size(self, ind):
        return round((self.asset * self.margin_rate) / MarketData2.ohlc_bot.close[ind] * 1.0/self.leverage, 2)

    def __add_action_log(self, log, i):
        self.action_log[str(i)+'-'+str(self.action_log_num)] = log
        self.action_log_num += 1
        self.i_log.append(i)

    def __calc_unrealized_pl(self, ind):
        lastp = MarketData2.ohlc_bot.close[ind]
        self.unrealized_pl = round((lastp - self.ave_holding_price) * self.ave_holding_size if self.holding_side ==     'buy' else (self.ave_holding_price - lastp) * self.ave_holding_size,2)

    def entry_order(self, side, price, size, ind, i):
        if self.cancel_all_orders_flg == False:
            n = len(self.unexe_side)
            self.unexe_side[n] = side
            self.unexe_price[n] = price
            self.unexe_size[n] = size
            self.unexe_dt[n] = MarketData2.ohlc_bot.close[ind]
            self.unexe_i[n] = i
            self.unexe_cancel[n] = False
            self.__add_action_log("Entry Order for " + side + " @" + str(price) + " x " + str(size),i)

    def exit_all_positions(self, ind, i):
        side = 'buy' if self.holding_side == 'sell' else 'sell'
        price = round((MarketData2.ohlc_bot.low[ind+1] + MarketData2.ohlc_bot.high[ind+1]) * 0.5)
        self.entry_order(side, price, self.ave_holding_size,ind,i)
        self.__add_action_log("Exit all",i)

    def pl_order(self, pl_kijun, ind, i):
        side = 'buy' if self.holding_side == 'sell' else 'sell'
        price = self.ave_holding_price + pl_kijun if self.holding_side == 'buy' else self.ave_holding_price - pl_kijun
        self.entry_order(side, price, self.ave_holding_size, ind, i)
        self.__add_action_log("Entry PL Order" + side + " @" + str(price) + " x " + str(self.ave_holding_size),i)

    def cancel_all_orders(self, ind, i):
        if len(self.unexe_side) > 0:
            self.cancel_all_orders_flg = True
            self.cancel_all_order_i = i
            self.__add_action_log("Cancelling All Orders",i)

    def cancel_order(self, unexe_index, ind, i):
        self.unexe_cancel[unexe_index] = True
        self.unexe_i[unexe_index] = i
        self.__add_action_log("Cancelling order #" + str(unexe_index),i)

    def __check_cancel(self, ind, i):
        if self.cancel_all_orders_flg:
            if self.cancel_all_order_i < i:
                self.__execute_cancel_all_orders()
        else:
            cancelled_index = ''
            for j in list(self.unexe_cancel.keys())[:]:
                if self.unexe_cancel[j] and self.unexe_i[j] < i:
                    self.__remove_unexe_ind(j)
                    cancelled_index += str(j) + ','
            if cancelled_index != '':
                self.__add_action_log("Cancelled orders #" + cancelled_index,i)

    def __execute_cancel(self, ind, i, unexe_ind):
        self.__remove_unexe_ind(unexe_ind)
        self.__add_action_log("Cancelled order #" + str(unexe_ind), i)

    def __execute_cancel_all_orders(self):
        self.__initialize_unexe_data()
        self.__initialize_cancel_all_orders()
        self.__add_action_log("Cancelled all orders",i)

    def __check_execution(self, ind, i):
        for j in list(self.unexe_side.keys())[:]:
            if self.unexe_i[j] < i:
                if self.unexe_side[j] == 'buy' and MarketData2.ohlc_bot.low[ind] <= self.unexe_price[j]:
                    self.__execute(j, ind, i)
                elif self.unexe_side[j] == 'sell' and MarketData2.ohlc_bot.high[ind] >= self.unexe_price[j]:
                    self.__execute(j, ind, i)

    def __execute(self, unexe_ind, ind, i):
        if self.holding_side =='':
            self.holding_side = self.unexe_side[unexe_ind]
            self.ave_holding_size = self.unexe_size[unexe_ind]
            self.ave_holding_price = self.unexe_price[unexe_ind]
            self.last_entry_i = i
            self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
        elif self.holding_side == 'buy':
            if self.unexe_side[unexe_ind] == 'buy':
                self.ave_holding_size += self.unexe_size[unexe_ind]
                self.ave_holding_price = ((self.ave_holding_price * self.ave_holding_size) + (self.unexe_price[unexe_ind] * self.unexe_size[unexe_ind])) / (self.ave_holding_size + self.unexe_size[unexe_ind])
                self.last_entry_i = i
                self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
            elif self.unexe_side[unexe_ind] == 'sell':
                if self.unexe_size[unexe_ind] < self.ave_holding_size:
                    self.ave_holding_size -= self.unexe_size[unexe_ind]
                    self.update_cum_pl(ind, i, unexe_ind, self.unexe_price[unexe_ind], self.unexe_size[unexe_ind])
                elif self.unexe_size[unexe_ind] > self.ave_holding_size:
                    self.ave_holding_size = self.unexe_size[unexe_ind] - self.ave_holding_size
                    self.ave_holding_price = self.unexe_size[unexe_ind]
                    self.holding_side = 'sell'
                    self.last_entry_i = i
                    self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
                    self.__update_cum_pl(ind, i, unexe_ind, self.unexe_price[unexe_ind], self.unexe_size[unexe_ind])
                elif self.unexe_size[unexe_ind] == self.ave_holding_size:
                    self.__update_cum_pl(ind, i, unexe_ind, self.unexe_price[unexe_ind], self.unexe_size[unexe_ind])
                    self.__initialize_holding_data()
        elif self.holding_side == 'sell':
            if self.unexe_side[unexe_ind] == 'sell':
                self.ave_holding_size += self.unexe_size[unexe_ind]
                self.ave_holding_price = ((self.ave_holding_price * self.ave_holding_size) + (self.unexe_price[unexe_ind] * self.unexe_size[unexe_ind])) / (self.ave_holding_size + self.unexe_size[unexe_ind])
                self.last_entry_i = i
                self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
            elif self.unexe_side[unexe_ind] == 'buy':
                if self.unexe_size[unexe_ind] < self.ave_holding_size:
                    self.ave_holding_size -= self.unexe_size[unexe_ind]
                    self.__update_cum_pl(ind, i, unexe_ind, self.unexe_price[unexe_ind], self.unexe_size[unexe_ind])
                elif self.unexe_size[unexe_ind] > self.ave_holding_size:
                    self.ave_holding_size = self.unexe_size[unexe_ind] - self.ave_holding_size
                    self.ave_holding_price = self.unexe_size[unexe_ind]
                    self.holding_side = 'buy'
                    self.last_entry_i = i
                    self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
                    self.__update_cum_pl(ind, i, unexe_ind, self.unexe_price[unexe_ind], self.unexe_size[unexe_ind])
                elif self.unexe_size[unexe_ind] == self.ave_holding_size:
                    self.__update_cum_pl(ind, i, unexe_ind, self.unexe_price[unexe_ind], self.unexe_size[unexe_ind])
                    self.__initialize_holding_data()
        self.__add_action_log("Executed " + self.unexe_side[unexe_ind] + " @" + str(self.unexe_price[unexe_ind]) + " x " + str(self.unexe_size[unexe_ind]),i)
        self.__remove_unexe_ind(unexe_ind)

    def __update_cum_pl(self, ind, i, unexe_ind, price, size):
        pl = 0
        if self.holding_side == 'buy':
            if self.unexe_side[unexe_ind] == 'sell':
                pl = (price - self.ave_holding_price) * size
        elif self.holding_side == 'sell':
            if self.unexe_side[unexe_ind] == 'buy':
                pl = (self.ave_holding_price - price) * size
        self.num_trade += 1
        if pl > 0:
            self.num_win += 1
        self.realized_pl += pl
