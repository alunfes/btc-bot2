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
        self.__initialize_unexe_data()
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
                if (cls.ac.holding_side == 'buy' and (prediction[i] == 2 or prediction[i] == 0 or prediction[i] == 3)) or \
                        (cls.ac.holding_side=='sell' and (prediction[i] == 1 or prediction[i] == 0 or prediction[i] == 3)):
                    cls.ac.cancel_all_orders(ind,i)
                    if cls.ac.holding_side !='' :
                        cls.ac.exit_all_positions(ind,i)
                #ノーポジでオーダーが判定を逆の時にキャンセル。
                if cls.ac.holding_side =='':
                    for j in list(cls.ac.unexe_side.keys())[:]:
                        if (cls.ac.unexe_side[j] == 'buy' and (prediction[i] == 2 or prediction[i] == 0 or prediction[i] == 3)) or  (cls.ac.unexe_side[j]=='sell' and (prediction[i] == 1 or prediction[i] == 0 or prediction[i] == 3)):
                            cls.ac.cancell_order(j,ind,i)
            elif conservertive_trade==False: #non conservertive trade
                # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。
                if (cls.ac.holding_side == 'buy' and prediction[i] == 2) or \
                        (cls.ac.holding_side == 'sell' and prediction[i] == 1):
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





'''
New Entry:
self.order_size = outstanding size
self.posi_size = executed size

PL:
self.order_size = outstanding size
self.posi_size = original posi size - executed size

'''



'''
オーダー全キャセル後に現在のポジションみて、price tracing完了後のポジション計算して、そうなるまで継続。
●オーダーのexecutedの合計がtarget sizeになるまで継続。

'''
@classmethod
def price_tracing_order(cls, side, size) -> float:
    if cls.flg_api_limit == False:
        print('started price tracing order')
        remaining_size = size
        sum_price_x_size = 0
        sum_size = 0
        pre_exe_size = 0
        price = cls.get_opt_price()
        order_id = cls.order_wait_till_boarding(side, price, remaining_size, 100)['child_order_acceptance_id']
        while remaining_size > 0:
            status = cls.get_order_status(order_id)
            if abs(price - cls.get_opt_price()) <= 300 and remaining_size > 0: #current order price is far from opt price
                res = cls.cancel_and_wait_completion(order_id)
                if len(res) > 0: #cancell failed order partially execugted
                    remaining_size = res['outstanding_size']
                    sum_price_x_size += float(res['average_price']) * float(res['executed_size'] - pre_exe_size)
                    sum_size += float(res['executed_size'] - pre_exe_size)
                    print('price tracing order - executed ' + str(res['executed_size']-pre_exe_size) + ' @' + str(res['average_price']))
                    if remaining_size <= 0: #target size has been executed
                        break
                    else: #place a new order for remaining size
                        pre_exe_size = status[0]['executed_size']
                        price = cls.get_opt_price()
                        order_id = cls.order_wait_till_boarding(side, price, remaining_size, 100)['child_order_acceptance_id']
                        print('price tracing order - executed ' + str(res['executed_size'] - pre_exe_size) + ' @' + str(res['average_price']))
                else:
                    price = cls.get_opt_price()
                    order_id = cls.order_wait_till_boarding(side, price, remaining_size, 100)['child_order_acceptance_id']
                    print('price tracing order - replaced order for '+side + ', @'+str(price)+' x '+str(remaining_size))
                    pre_exe_size = 0
            if len(status) > 0:
                if status[0]['outstanding_size'] == 0: #excuted all portion
                    sum_price_x_size += float(status[0]['average_price']) * float(status[0]['executed_size'] - pre_exe_size)
                    sum_size += float(status[0]['executed_size'] - pre_exe_size)
                    remaining_size = 0
                    pre_exe_size = 0
                    break
                else:
                    if status[0]['outstanding_size'] < remaining_size:
                        sum_price_x_size += float(status[0]['average_price']) * float(status[0]['executed_size'] - pre_exe_size)
                        sum_size += float(status[0]['executed_size'] - pre_exe_size)
                        remaining_size = status[0]['outstanding_size']
                        print('price tracing order - executed '+str(status[0]['executed_size'] - pre_exe_size) + ' @'+str(price))
                        pre_exe_size = status[0]['executed_size']
            time.sleep(0.2)
        print('ave price={}, exe size = {}'.format(sum_price_x_size / sum_size, sum_size))
        return sum_price_x_size / sum_size
    else:
        print('order is temporary exhibited due to API access limitation!')
        return ''