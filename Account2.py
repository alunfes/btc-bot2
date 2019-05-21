'''
for tick level simulation.
'''



class Account2:
    def __init__(self):
        self.__initialize_order()
        self.__initialize_holding()

        self.base_margin_rate = 1.2
        self.leverage = 15.0
        self.slip_page = 500
        self.force_loss_cut_rate = 0.5
        self.initial_asset = 5000
        self.order_cancel_delay = 3
        self.prediction_delay = 3

        self.total_pl = 0
        self.realized_pl = 0
        self.current_pl = 0
        self.num_trade = 0
        self.num_win = 0
        self.win_rate = 0
        self.asset = self.initial_asset

        self.total_pl_log = []
        self.predicton_log=[]
        self.action_log = []
        self.i_log = []
        self.action_log = {}
        self.log = []
        self.action_log_num = 0


    def __initialize_order(self):
        self.order_side = ''
        self.order_price = 0
        self.order_size = 0
        self.order_i = 0
        self.order_dt = ''
        self.order_type = ''
        self.order_cancel = False
        self.order_expire = 0

    def __initialize_holding(self):
        self.holding_side = ''
        self.holding_price = 0
        self.holding_size = 0
        self.holding_i = 0
        self.holding_dt = ''


    def move_to_next(self,  i, price):
        self.__check_loss_cut(i,price)
        self.__check_execution(i,price)
        self.__check_cancel(i)
        if self.order_side != '':
            self.current_pl = (price - self.holding_price) * self.holding_size if self.holding_side == 'buy' else (self.holding_price - price) * self.holding_size
        else:
            self.current_pl = 0
        self.total_pl = self.realized_pl + self.current_pl
        self.total_pl_log.append(self.total_pl)
        self.asset = self.initial_asset + self.total_pl
        self.__add_action_log('i:'+str(i)+'order='+self.order_side+', '+str(self.order_size)+' @'+str(self.order_price),i)
        if self.holding_side !='':
            print('i={},posi={},posi price={},posi size={},order side={},order price={},order size={},pl={},realize pl={},current pl={}'
                  .format(i,self.holding_side,self.holding_price,self.holding_size,self.order_side,self.order_price,self.order_size,self.total_pl,self.realized_pl,self.current_pl))

    def last_day_operation(self,i, price):
        self.__check_loss_cut( i,price)
        self.__check_execution( i,price)
        self.__check_cancel( i)
        if self.holding_side != '':
            if self.order_side != '':
                self.current_pl = (price - self.holding_price) * self.holding_size if self.holding_side == 'buy' else (self.holding_price -price) * self.holding_size
            else:
                self.current_pl = 0
        self.total_pl = self.realized_pl + self.current_pl
        self.total_pl_log.append(self.total_pl)
        if self.num_trade > 0:
            self.win_rate = self.num_win / self.num_trade


    def entry_order(self, side, price, size, type,  expire, i):
        if self.order_side =='':
            self.order_side = side
            self.order_price = price
            self.order_size  =size
            self.order_i = i
            self.order_type = type #limit, market
            self.order_cancel = False
            self.order_expire = expire
        else:
            print('order is already exist!')


    def cancel_order(self,  i):
        if self.order_type != 'losscut':
            self.order_cancel = True
            self.order_i = i

    def __check_cancel(self,i):
        if self.order_cancel:
            if i - self.order_i >= self.order_cancel_delay:
                self.__add_action_log('order cancelled.',i)
                self.log.append('order cancelled.')
                self.__initialize_order()

    def __check_expiration(self,i):
        if i - self.order_i >= self.order_expire and self.order_type != 'market' and self.order_type != 'losscut':
            self.__add_action_log('order expired.', i)
            self.log.append('order expired.')
            self.__initialize_order()

    def __check_execution(self,  i, price):
        if i - self.order_i >= self.order_cancel_delay and self.order_side !='':
            if self.order_type == 'market' or self.order_type == 'losscut':
                self.__process_execution(price,i)
                self.__initialize_order()
            elif self.order_type == 'limit' and ((self.order_side == 'buy' and self.order_price >= price) or (self.order_side == 'sell' and self.order_price <= price)):
                self.__process_execution(self.order_price,i)
                self.__initialize_order()
            elif self.order_type != 'market' and self.order_type != 'limit' and self.order_type != 'losscut':
                print('Invalid order type!' + self.order_type)

    def __process_execution(self, price,  i):
        if self.order_side != '':
            if self.holding_side == '':  # no position
                self.holding_side = self.order_side
                self.holding_price = price
                self.holding_size = self.order_size
                self.holding_i = self.order_i
            else:
                if self.holding_side == self.order_side:  # order side and position side is matched
                    self.holding_price = round(((self.holding_price * self.holding_size) + (price * self.order_size)) / (self.order_size + self.holding_size))
                    self.holding_size += self.order_size
                    self.holding_i = i
                elif self.holding_size > self.order_size:  # side is not matched and holding size > order size
                    self.__calc_executed_pl(price, i)
                    self.holding_size -= self.order_size
                    #self.realized_pl = (price - self.holding_price) * self.order_size if self.holding_side == 'buy' else (self.holding_price - price) * self.order_size
                elif self.holding_size == self.order_size:
                    self.__calc_executed_pl(price, i)
                    self.__initialize_holding()
                else:  # in case order size is bigger than holding size
                    self.__calc_executed_pl(price, i)
                    self.holding_side = self.order_side
                    self.holding_size = self.order_size - self.holding_size
                    self.holding_price = price
                    self.holding_i = i



    def __calc_executed_pl(self,price,i): #assume all order size was executed
        pl = (price - self.holding_price) * self.order_size if self.holding_side == 'buy' else (self.holding_price - price) * self.order_size
        self.realized_pl += round(pl)
        self.num_trade += 1
        if pl >0:
            self.num_win +=1

    def __check_loss_cut(self,  i, price):
        if self.holding_side != '' and self.order_type !='losscut':
            req_collateral = self.holding_size * price / self.leverage
            pl = price - self.holding_price if self.holding_side == 'buy' else self.holding_price - price
            pl = pl * self.holding_size
            margin_rate = (self.initial_asset + self.realized_pl + pl) / req_collateral
            if margin_rate <= self.force_loss_cut_rate:
                self.__add_action_log("Loss cut postion! margin_rate=" + str(margin_rate),i)
                self.log.append("Loss cut postion! margin_rate=" + str(margin_rate))
                self.__force_exit(i)

    def __force_exit(self,  i):
        self.order_side = 'buy' if self.holding_side == 'sell' else 'sell'
        self.order_size = self.holding_size
        self.order_type = 'losscut'
        self.order_i = i

    def __add_action_log(self, log, i):
        self.action_log[str(i)+'-'+str(self.action_log_num)] = log
        self.action_log_num += 1
        self.i_log.append(i)
