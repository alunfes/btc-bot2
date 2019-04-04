import threading
import xgboost as xgb
import pandas as pd
import time
from SystemFlg import SystemFlg
from XgbModel import XgbModel
from MarketData import MarketData
from MarketData2 import MarketData2
from CryptowatchDataGetter import CryptowatchDataGetter
from Trade import Trade
from datetime import datetime
import copy



class Bot:
    def initialize(self, size, pl_kijun):
        self.trade_size = size
        self.pl_kijun = pl_kijun
        self.posi_side = ''
        self.posi_id = ''
        self.posi_price = 0
        self.posi_size = 0
        self.posi_status = ''
        self.order_side = ''
        self.order_id = ''
        self.order_price = 0
        self.order_size = 0
        self.order_status = ''
        self.order_dt = ''

        self.pl = 0
        self.pl_log = []
        self.num_trade = 0
        self.num_win = 0
        self.win_rate = 0

    def calc_and_log_pl(self, ave_p, size):
        pl = (ave_p - self.posi_price) * self.posi_size if self.posi_side == 'buy' else (self.posi_price - ave_p) * self.posi_size
        self.pl += pl
        self.pl_log.append(self.pl)
        self.num_trade += 1
        if pl > 0:
            self.num_win += 1
        self.win_rate = float(self.num_win) / float(self.num_trade)
        print('pl = {}, num = {}, win_rate = {}'.format(self.pl, self.num_trade, self.win_rate))


    def entry_order(self, side, price, size):
        self.order_id = Trade.order(side, price, size, 1)
        self.order_side = side
        self.order_price = price
        self.order_size = size
        self.order_status = 'new entrying'
        self.order_dt = datetime.now()
        print('new entry: side = {}, price = {}, size = {}'.format(side, price, size))

    def pl_order(self):
        side = 'buy' if self.posi_side == 'sell' else 'sell'
        price = self.posi_price + self.pl_kijun if self.posi_side == 'buy' else self.posi_price - self.pl_kijun
        self.order_id = Trade.order(side, price, self.posi_size, 100)
        self.order_price = price
        self.order_size = self.posi_size
        self.order_status = 'pl ordering'
        self.order_dt = datetime.now()
        print('pl order: side = {}, price = {}, size = {}'.format(self.order_side, self.order_price, self.order_size))


    def exit_order(self):
        print('exit order')
        Trade.cancel_and_wait_completion(self.order_id) #cancel pl order
        side = 'buy' if self.posi_side == 'sell' else 'sell'
        ave_p = Trade.price_tracing_order(side, self.posi_size)
        self.calc_and_log_pl(ave_p, self.posi_size)
        self.posi_side = ''
        self.posi_id = ''
        self.posi_price = 0
        self.posi_size = 0
        self.posi_status = ''
        self.order_side = ''
        self.order_id = ''
        self.order_price = 0
        self.order_size = 0
        self.order_status = ''
        self.order_dt = ''


    def cancel_order(self):
        print('cancel order')
        status = Trade.cancel_and_wait_completion(self.order_id)
        if len(status) > 0:
            print('cancel failed, partially executed')
            ave_p = Trade.price_tracing_order(status[0]['side'].lower(), status[0]['executed_size'])
            self.calc_and_log_pl(ave_p, status[0]['executed_size'])
            self.posi_side = ''
            self.posi_id = ''
            self.posi_price = 0
            self.posi_size = 0
            self.posi_status = ''
            self.order_side = ''
            self.order_id = ''
            self.order_price = 0
            self.order_size = 0
            self.order_status = ''
            self.order_dt = ''
        else:
            self.order_side = ''
            self.order_id = ''
            self.order_price = 0
            self.order_size = 0
            self.order_status = ''
            self.order_dt = ''

    def check_execution(self):
        status = Trade.get_order_status(self.order_id)
        if len(status) > 0:
            if int(status[0]['outstanding_size']) == 0 and self.order_status != 'new entrying': #pl is fully executed
                self.calc_and_log_pl(status[0]['average_price'], status[0]['executed_size'])
                self.order_side = ''
                self.order_id = ''
                self.order_price = 0
                self.order_size = 0
                self.order_status = ''
                self.order_size = 0
                self.posi_side = ''
                self.posi_price = 0
                self.posi_size = 0
                self.posi_status = ''
            else:
                if int(status[0]['outstanding_size']) == 0: #new entry has been fully executed
                    print('entry order has been fully executed')
                    self.order_side = ''
                    self.order_id = ''
                    self.order_price = 0
                    self.order_size = 0
                    self.order_status = ''
                    self.posi_side = status[0]['side'].lower()
                    self.posi_price = status[0]['average_price']
                    self.posi_size = status[0]['executed_size']
                    self.posi_status = 'fully executed'
                    print('current position: side = {}, price = {}, size = {}'.format(self.posi_side, self.posi_price, self.posi_size))
                elif int(status[0]['outstanding_size']) > 0: #entry order has been partially executed
                    print('entry order partially executed')
                    self.order_size = status[0]['executed_size']
                    self.order_status = 'partially executed'
                    self.posi_status = 'partially executed'
                    self.posi_side = status[0]['side'].lower()
                    self.posi_price = status[0]['average_price']
                    self.posi_size = status[0]['executed_size']
                    print('current position: side = {}, price = {}, size = {}'.format(self.posi_side, self.posi_price,
                                                                                      self.posi_size))
        elif (datetime.now() - self.order_dt).total_seconds() >= 60: #order has been expired
            self.order_side = ''
            self.order_id = ''
            self.order_price = 0
            self.order_size = 0
            self.order_status = ''
            self.order_dt = ''
            print('order has been expired')
        else:
            print('') #maybe order is not yet boarded


    def start_bot(self,size, pl_kijun):
        self.initialize(size, pl_kijun)
        print('bot - updating crypto data..')
        CryptowatchDataGetter.get_and_add_to_csv()
        print('bot - initializing MarketData2..')
        MarketData2.initialize_from_bot_csv(100, 30, 500)
        train_df = MarketData2.generate_df(MarketData2.ohlc_bot)
        #print(train_df)
        model = XgbModel()
        print('bot - training xgb model..')
        train_x, test_x, train_y, test_y = model.generate_data(copy.deepcopy(train_df), 1)
        #print('x shape '+str(train_x.shape))
        #print('y shape '+str(train_y.shape))
        bst = model.train(train_x, train_y)
        print('bot - training completed..')
        print('bot - updating crypto data..')
        CryptowatchDataGetter.get_and_add_to_csv()
        MarketData2.initialize_from_bot_csv(100, 30, 500)
        MarketData2.ohlc_bot.cut_data(1000)
        print('bot - started bot loop.')
        while SystemFlg.get_system_flg():
            if datetime.now().second == 1:
                res, omd = CryptowatchDataGetter.get_data_after_specific_ut(MarketData2.ohlc_bot.unix_time[-1])
                if res == 0:
                    for i in range(len(omd.dt)):
                        MarketData2.ohlc_bot.add_and_pop(omd.unix_time[i],omd.dt[i], omd.open[i], omd.high[i], omd.low[i], omd.close[i], omd.size[i])
                    MarketData2.update_ohlc_index_for_bot2()
                    df = MarketData2.generate_df_for_bot(copy.deepcopy(MarketData2.ohlc_bot))
                    pred_x = model.generate_bot_pred_data(df)
                    predict = bst.predict(xgb.DMatrix(pred_x))
                    print('dt={}, open={}, close={}, predict={}'.format(MarketData2.ohlc_bot.dt[-1],MarketData2.ohlc_bot.open[-1],
                                                                        MarketData2.ohlc_bot.close[-1], predict[0]))
                else:
                    print('crypto watch data download error!')
            if self.posi_side == '' and self.order_side == '': #no position no order
                if predict[0] == 1:
                    self.entry_order('buy', MarketData2.ohlc_bot.close[-1], self.trade_size)
                elif predict[0] == 2:
                    self.entry_order('sell', MarketData2.ohlc_bot.close[-1], self.trade_size)
            elif self.posi_side == '' and self.order_side != '': #no position and ordering
                if (self.order_side == 'buy' and (predict[0] == 2 or predict[0] == 0)) or (self.order_side == 'sell' and (predict[0] == 1 or predict[0] == 0)):
                    self.cancel_order()
            elif self.posi_side != '' and self.order_side == '': #holding position and no order
                self.pl_order()
            elif self.posi_side == 'buy' and (predict[0] == 2 or predict[0] == 0) or self.posi_side == 'sell' and (predict[0] == 1 or predict[0] == 0): #exit when oposit predict
                self.exit_order()
            if self.order_side != '':
                self.check_execution()
            time.sleep(0.5)




if __name__ == '__main__':
    SystemFlg.initialize()
    bot = Bot()
    bot.start_bot()





