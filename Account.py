from MarketData2 import  MarketData2
from numba import jit, f8, i8, b1, void


class Account:
    def __init__(self, pl_kijun):
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

        self.base_margin_rate = 1.2
        self.leverage = 15.0
        self.slip_page = 500
        self.force_loss_cut_rate = 0.5

        self.base_pl_kijun = pl_kijun

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

    #@jit(void(void))
    def __initialize_unexe_data(self):
        self.unexe_price = {}
        self.unexe_size = {}
        self.unexe_side = {}
        self.unexe_i = {}
        self.unexe_expire = {}
        self.unexe_dt = {}
        self.unexe_cancel = {}
        self.unexe_info = {}
        self.unexe_ifd = {} #True / False
        self.unexe_ifd_plkijun = {} #if done pl kijun
        self.index_num = 0


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
        self.unexe_expire.pop(unexe_key)
        self.unexe_dt.pop(unexe_key)
        self.unexe_cancel.pop(unexe_key)
        self.unexe_info.pop(unexe_key)
        self.unexe_ifd.pop(unexe_key)
        self.unexe_ifd_plkijun.pop(unexe_key)

    def move_to_next(self, prediction, pl_kijun, ind, i):
        self.__check_execution(prediction, ind, i)
        self.__check_cancel(ind, i)
        self.__check_and_do_force_loss_cut(ind,i)
        self.__calc_unrealized_pl(ind)
        self.realized_pl_log[i] = self.realized_pl
        self.total_pl = round(self.realized_pl + self.unrealized_pl)
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
        if len(self.unexe_i) == 0:
            self.__initialize_unexe_data()
        self.__add_action_log('Moved to next:'+'ohlc='+str(MarketData2.ohlc_bot.open[ind])+','+str(MarketData2.ohlc_bot.high[ind])+','+str(MarketData2.ohlc_bot.low[ind])+','+str(MarketData2.ohlc_bot.close[ind])+', posi='+self.holding_side+' @'+str(self.ave_holding_price)+', pl='+str(self.total_pl)+', num orders='+str(len(self.unexe_i))+', predict='+str(prediction),i)
        if len(self.unexe_i) > 0:
            key = list(self.unexe_i.keys())[0]
            print('order side='+self.unexe_side[key])
            print('order info='+self.unexe_info[key])
            print('order price='+str(self.unexe_price[key]))
            print('order IFD='+str(self.unexe_ifd[key]))
            print('order IFD_kijun='+str(self.unexe_ifd_plkijun[key]))
            print('posi side='+self.holding_side)
            print('posi price='+str(self.ave_holding_price))
            print('posi size='+str(self.ave_holding_size))


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
        return round((self.asset * self.leverage) / (MarketData2.ohlc_bot.close[ind] * 1.0 * self.base_margin_rate),2)

    def __check_and_do_force_loss_cut(self, ind, i):
        if self.ave_holding_size > 0:
            req_collateral = self.ave_holding_size * MarketData2.ohlc_bot.close[ind] / self.leverage
            pl = (MarketData2.ohlc_bot.low[ind] - self.ave_holding_price) if self.holding_side == 'buy' else (self.ave_holding_price - MarketData2.ohlc_bot.high[ind])
            pl = pl * self.ave_holding_size
            margin_rate = (self.initial_asset+self.realized_pl+pl) / req_collateral
            if margin_rate <= self.force_loss_cut_rate:
                self.__add_action_log("Loss cut postion! margin_rate=" +str(margin_rate),i)
                self.__force_exit(ind, i)
            else:
                pass
        else:
            pass

    def __add_action_log(self, log, i):
        self.action_log[str(i)+'-'+str(self.action_log_num)] = log
        self.action_log_num += 1
        self.i_log.append(i)
        orders = ''
        for key in self.unexe_i.keys():
            orders += 'order key='+str(key)+', i='+str(self.unexe_i[key]) + ', info='+str(self.unexe_info[key])+', expire='+str(self.unexe_expire[key]) +' , '
        print('i='+str(i)+':'+log + ':'+orders)

    def __calc_unrealized_pl(self, ind):
        lastp = MarketData2.ohlc_bot.close[ind]
        self.unrealized_pl = round((lastp - self.ave_holding_price) * self.ave_holding_size if self.holding_side == 'buy' else (self.ave_holding_price - lastp) * self.ave_holding_size)

    def entry_order(self, side, price, size, info, expire, ifd, ifd_plkijun, ind, i):
        if self.cancel_all_orders_flg == False:
            self.unexe_side[self.index_num] = side
            self.unexe_price[self.index_num] = price
            self.unexe_size[self.index_num] = size
            self.unexe_dt[self.index_num] = MarketData2.ohlc_bot.close[ind]
            self.unexe_i[self.index_num] = i
            self.unexe_expire[self.index_num] = expire
            self.unexe_cancel[self.index_num] = False
            self.unexe_info[self.index_num] = info
            self.unexe_ifd[self.index_num] = ifd
            self.unexe_ifd_plkijun[self.index_num] = ifd_plkijun
            self.index_num += 1
            self.__add_action_log("Entry Order for " + side + " @" + str(price) + " x " + str(size)+' ifd='+str(ifd)+', pl kijun='+str(ifd_plkijun),i)

    '''
    should be used only when place pl order after execution of IFD
    '''
    def __immediate_entry(self, side,price, size, info, expire, ifd, ifd_plkijun, ind, i):
        self.unexe_side[self.index_num] = side
        self.unexe_price[self.index_num] = price
        self.unexe_size[self.index_num] = size
        self.unexe_dt[self.index_num] = MarketData2.ohlc_bot.close[ind]
        self.unexe_i[self.index_num] = i
        self.unexe_expire[self.index_num] = expire
        self.unexe_cancel[self.index_num] = False
        self.unexe_info[self.index_num] = info
        self.unexe_ifd[self.index_num] = ifd
        self.unexe_ifd_plkijun[self.index_num] = ifd_plkijun
        self.index_num += 1
        self.__add_action_log("Immediate Entry Order for " + side + " @" + str(price) + " x " + str(size)+' ifd='+str(ifd)+', pl kijun='+str(ifd_plkijun),i)


    def exit_all_positions(self, ind, i):
        if self.ave_holding_size > 0:
            self.__force_exit(ind, i)
            self.__add_action_log("exit_all_positions" ,i)

    '''
    次の分足のmiddle priceでexit
    '''
    def __force_exit(self, ind, i):
        price = round((MarketData2.ohlc_bot.low[ind + 1] + MarketData2.ohlc_bot.high[ind + 1]) * 0.5)
        pl = (price - self.ave_holding_price) * self.ave_holding_size if self.holding_side == 'buy' else (self.ave_holding_price - price) * self.ave_holding_size
        self.num_trade += 1
        if pl > 0:
            self.num_win += 1
        self.realized_pl += pl
        self.__add_action_log("Force exited position. " + self.holding_side + " @" + str(price) + " x " + str(self.ave_holding_size), i)
        self.__initialize_holding_data()

    def pl_order(self, pl_kijun, ind, i):
        side = 'buy' if self.holding_side == 'sell' else 'sell'
        price = self.ave_holding_price + pl_kijun if self.holding_side == 'buy' else self.ave_holding_price - pl_kijun
        self.entry_order(side, price, self.ave_holding_size, 'pl order', 1440, False, 0, ind, i)
        self.__add_action_log("Entry PL Order" + side + " @" + str(price) + " x " + str(self.ave_holding_size),i)

    def cancel_all_orders(self, ind, i):
        if len(self.unexe_side) > 0 and self.cancel_all_orders_flg == False:
            self.cancel_all_orders_flg = True
            self.cancel_all_order_i = i
            self.__add_action_log("Cancelling All Orders",i)

    def cancel_order(self, unexe_key, ind, i):
        if unexe_key in self.unexe_side:
            self.unexe_cancel[unexe_key] = True
            self.__add_action_log("Cancelling Order, id="+str(unexe_key), i)


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

    def __execute_cancel(self, ind, i, unexe_key):
        self.__remove_unexe_key(unexe_key)
        self.__add_action_log("Cancelled order #" + str(unexe_key), i)

    def __execute_cancel_all_orders(self, i):
        self.__initialize_unexe_data()
        self.__initialize_cancel_all_orders()
        self.__add_action_log("Cancelled all orders",i)

    def __check_execution(self, prediction, ind, i):
        for j in list(self.unexe_side.keys())[:]:
            if self.unexe_i[j] < i:
                if self.unexe_side[j] == 'buy' and MarketData2.ohlc_bot.low[ind] <= self.unexe_price[j]:
                    self.__execute(j, prediction, ind, i)
                elif self.unexe_side[j] == 'sell' and MarketData2.ohlc_bot.high[ind] >= self.unexe_price[j]:
                    self.__execute(j, prediction,ind, i)
                elif self.unexe_expire[j] <= i - self.unexe_i[j]:
                    self.__add_action_log("Expired order - "+str(j), i)
                    print("Expired order - "+str(j))
                    self.__remove_unexe_key(j)

    #@jit(void(i8,i8,i8,i8))
    def __execute(self, unexe_key, prediction, ind, i):
        if self.holding_side == '': #in case of new entry execution
            self.holding_side = self.unexe_side[unexe_key]
            self.ave_holding_size = self.unexe_size[unexe_key]
            self.ave_holding_price = self.unexe_price[unexe_key]
            self.last_entry_i = i
            self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
            self.__add_action_log("New Entry Executed " + self.unexe_side[unexe_key] + " @" + str(self.unexe_price[unexe_key]) + " x " + str(self.unexe_size[unexe_key]), i)
            if self.unexe_ifd[unexe_key]: #IFD pl order
                self.__process_ifd_execution(unexe_key, ind, i)
        else:
            self.__process_normal_execution(unexe_key, prediction, ind, i)
        if unexe_key in self.unexe_i.keys():
            self.__remove_unexe_key(unexe_key)

    '''
    after execution of 
    execute pl order for multiple times in one minute.
    then 
    '''
    #@jit(void(i8,i8,i8))
    def __process_ifd_execution(self, unexe_key, ind, i):
        if (self.holding_side == 'buy' and MarketData2.ohlc_bot.high[ind] >= self.ave_holding_price +self.unexe_ifd_plkijun[unexe_key]) or \
                (self.holding_side == 'sell' and MarketData2.ohlc_bot.low[ind] <= self.ave_holding_price -self.unexe_ifd_plkijun[unexe_key]):  # when pl execute soon after new IFD entry
            num = 0
            pl = 0
            pl_side = 'buy' if self.holding_side == 'sell' else 'buy'
            if (MarketData2.ohlc_bot.high[ind] - self.ave_holding_price) / self.unexe_ifd_plkijun[unexe_key] <= 2.0 or \
                    (self.ave_holding_price - MarketData2.ohlc_bot.low[ind]) / self.unexe_ifd_plkijun[unexe_key] <= 2.0:  # pl exection and reentry
                num = 1
                pl = round(self.unexe_ifd_plkijun[unexe_key] * self.ave_holding_size)
                self.ave_holding_price = self.ave_holding_price + self.unexe_ifd_plkijun[unexe_key] if \
                    self.unexe_side[unexe_key] == 'buy' else self.ave_holding_price - self.unexe_ifd_plkijun[unexe_key]
                self.__immediate_entry(pl_side, \
                                       self.ave_holding_price+self.unexe_ifd_plkijun[unexe_key] if self.holding_side == 'buy' else self.ave_holding_price-self.unexe_ifd_plkijun[unexe_key], \
                                       self.unexe_size[unexe_key],'immediate pl order', 1440, False,0,ind,i)
                self.__add_action_log("PL Executed and re-entry, num=" + str(num) + ', total pl=' + str(pl) + ', new entry price=' + str(self.ave_holding_price), i)
            else:  # multiple pl execution and rentry
                if self.holding_side == 'buy':
                    num = 1 + round(0.5 * ((MarketData2.ohlc_bot.high[ind] - self.ave_holding_price -self.unexe_ifd_plkijun[unexe_key]) / self.unexe_ifd_plkijun[unexe_key]))
                    pl = self.unexe_ifd_plkijun[unexe_key] * self.ave_holding_size + \
                         round(0.5 * (MarketData2.ohlc_bot.high[ind] - self.ave_holding_price + self.unexe_ifd_plkijun[unexe_key]) * self.ave_holding_size)
                    self.ave_holding_price = MarketData2.ohlc_bot.high[ind] + round(self.unexe_ifd_plkijun[unexe_key] * 0.5)
                    self.__immediate_entry(pl_side, self.ave_holding_price + self.unexe_ifd_plkijun[unexe_key],self.unexe_size[unexe_key], 'immediate pl order', 1440, False,0, ind, i)
                else:  # in case of sell
                    num = 1 + round(0.5 * ((self.ave_holding_price - MarketData2.ohlc_bot.low[ind] - self.unexe_ifd_plkijun[unexe_key]) / self.unexe_ifd_plkijun[unexe_key]))
                    pl = round(self.unexe_ifd_plkijun[unexe_key] * self.ave_holding_size + \
                         round(0.5 * (self.ave_holding_price - MarketData2.ohlc_bot.low[ind] + self.unexe_ifd_plkijun[unexe_key]) * self.ave_holding_size))
                    self.ave_holding_price = MarketData2.ohlc_bot.low[ind] - round(self.unexe_ifd_plkijun[unexe_key] * 0.5)
                    self.__immediate_entry(pl_side, self.ave_holding_price -self.unexe_ifd_plkijun[unexe_key], self.unexe_size[unexe_key], 'immediate pl order', 1440, False,0, ind, i)
                self.__add_action_log("Multi PL Executed and re-entry, num=" + str(num) + ', total pl=' + str(pl) + ', new entry price=' + str(self.ave_holding_price), i)
            self.__remove_unexe_key(unexe_key)
            self.last_entry_i = i
            self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
            self.num_trade += num
            self.realized_pl += pl
            self.num_win += num
        else:  # entry pl order when 
            side = 'buy' if self.holding_side == 'sell' else 'sell'
            price = self.ave_holding_price + self.unexe_ifd_plkijun[unexe_key] if self.holding_side == 'buy' else self.ave_holding_price - self.unexe_ifd_plkijun[unexe_key]
            self.__immediate_entry(side, price, self.ave_holding_size, 'pl order', 1440, False, 0, ind, i)
            self.__add_action_log("Entry PL Order as a result of IFD" + side + " @" + str(price) + " x " + str(self.ave_holding_size), i)

    '''
    pl execution for normal pl and IFD pl execution (exclude pl exe soon after new entry)
    '''
    #@jit(void(i8, i8, i8))
    def __process_normal_pl_execution(self, unexe_key, prediction, ind, i):
        if 'pl' in self.unexe_info[unexe_key]:
            if (self.holding_side == 'buy' and self.unexe_side[unexe_key] == 'sell') or (self.holding_side == 'sell' and self.unexe_side[unexe_key] == 'buy'):
                if self.ave_holding_size == self.unexe_size[unexe_key]:  # if all position can be closed by pl execution
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                    self.__add_action_log('Normal PL Executed. price=' + str(self.unexe_price[unexe_key]) + ', size=' + str(self.unexe_size[unexe_key]), i)
                    self.__initialize_holding_data()
                    if prediction == 1 or prediction == 2:
                        side = 'buy' if prediction ==1 else 'sell'
                        price = self.unexe_price[unexe_key]
                        size = self.unexe_size[unexe_key]
                        self.__immediate_entry(side,price,size,'new entry after normal pl execution',1,True, self.base_pl_kijun,ind,i)
                        self.__add_action_log('Re-entry after normal PL Executed. price=' + str(price) + ', size=' + str(size), i)
                    self.__remove_unexe_key(unexe_key)
                elif self.ave_holding_size < self.unexe_size[unexe_key]:  # if pl order size if bigger than position size
                    print('pl size is bigger than position size!')
                    self.__add_action_log('pl size is bigger than position size!', i)
                    self.ave_holding_size = self.unexe_size[unexe_key] - self.ave_holding_size
                    self.holding_side = self.unexe_side[unexe_key]
                    self.ave_holding_price = self.unexe_price[unexe_key]
                    self.last_entry_i = i
                    self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
                    self.__remove_unexe_key(unexe_key)
                else:  # if pl size is smaller than position size
                    print('pl size is smaller than position size!')
                    self.__add_action_log('pl size is smaller than position size!', i)
                    self.ave_holding_size -= self.unexe_size[unexe_key]
                    self.last_entry_i = i
                    self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                    self.__remove_unexe_key(unexe_key)
            else:
                print('order side and holding side are same in normal pl order!')
                self.__add_action_log('order side and holding side are same in normal pl order!', i)
        else:
            print('pl is not included in unexe_info but tried to process normal pl order! Do nothing.')
            self.__add_action_log('pl is not included in info but tried to process normal pl order! Do nothing.', i)

    #@jit(void(i8, i8, i8))
    def __process_normal_execution(self, unexe_key, prediction, ind, i):
        if 'pl' in self.unexe_info[unexe_key]:
            self.__process_normal_pl_execution(unexe_key, prediction, ind, i)
            #print('pl is in order info but tried to process normal execution! Do nothing.')
            #self.__add_action_log('pl is in order info but tried to process normal execution! Do nothing.', i)
        else:
            if (self.holding_side == 'buy' and self.unexe_side[unexe_key] == 'sell') or (
                    self.holding_side == 'sell' and self.unexe_side[unexe_key] == 'buy'):  # order side is not position side
                if self.ave_holding_size == self.unexe_size[unexe_key]:
                    self.__add_action_log('processed normal execution' + 'order side=' + self.unexe_side[
                        unexe_key] + ', order size=' + str(self.unexe_size[unexe_key]), i)
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                    self.__initialize_holding_data()
                elif self.ave_holding_size > self.unexe_size[unexe_key]:
                    self.ave_holding_size -= self.unexe_size[unexe_key]
                    self.__add_action_log('processed normal execution' + 'order side=' + self.unexe_side[
                        unexe_key] + ', order size=' + str(self.unexe_size[unexe_key]), i)
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                elif self.ave_holding_size < self.unexe_size[unexe_key]:  # executed size if bigger than position size
                    self.ave_holding_size = self.ave_holding_size - self.unexe_size[unexe_key]
                    self.holding_side = self.unexe_side[unexe_key]
                    self.ave_holding_price = self.unexe_price[unexe_key]
                    self.__add_action_log('processed normal execution' + 'order side=' + self.unexe_side[
                        unexe_key] + ', order size=' + str(self.unexe_size[unexe_key]), i)
                    self.__update_cum_pl(ind, i, unexe_key, self.unexe_price[unexe_key], self.unexe_size[unexe_key])
                    self.last_entry_i = i
                    self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
            elif (self.holding_side == 'buy' and self.unexe_side[unexe_key] == 'buy') or (
                    self.holding_side == 'sell' and self.unexe_side[unexe_key] == 'sell'):
                self.ave_holding_price = ((self.ave_holding_price * self.ave_holding_size) + (
                            self.unexe_price[unexe_key] * self.unexe_size[unexe_key])) / (
                                                     self.ave_holding_size + self.unexe_size[unexe_key])
                self.ave_holding_size += self.unexe_size[unexe_key]
                self.last_entry_i = i
                self.last_entry_time = MarketData2.ohlc_bot.dt[ind]
            else:
                print('__process_normal_execution - this function should be used after ')

    def __update_cum_pl(self, ind, i, unexe_key, price, size):
        pl = 0
        if self.holding_side == 'buy':
            if self.unexe_side[unexe_key] == 'sell':
                pl = round((price - self.ave_holding_price) * size)
        elif self.holding_side == 'sell':
            if self.unexe_side[unexe_key] == 'buy':
                pl = round((self.ave_holding_price - price) * size)
        self.num_trade += 1
        if pl > 0:
            self.num_win += 1
        self.realized_pl += pl



