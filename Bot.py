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

        self.pl = 0
        self.pl_log = []
        self.num_trade = 0
        self.num_win = 0
        self.win_rate = 0

    def entry_order(self, side, price, size):
        self.order_id = Trade.order(side, price, size, 1)
        self.order_side = side
        self.order_price = price
        self.order_size = size
        self.order_status = 'new entrying'

    def pl_order(self):
        side = 'buy' if self.posi_side == 'sell' else 'sell'
        price = self.posi_price + self.pl_kijun if self.posi_side == 'buy' else self.posi_price - self.pl_kijun
        self.order_id = Trade.order(side, price, self.posi_size, 100)
        self.order_price = price
        self.order_size = self.posi_size
        self.order_status = 'pl ordering'


    def exit_order(self):
        side = 'buy' if self.posi_side == 'sell' else 'sell'
        Trade.price_tracing_order(side, self.posi_size)
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


    def cancel_order(self):
        status = Trade.cancel_and_wait_completion(self.order_id)
        status = Trade.get_order_status(self.order_id)
        if len(status) > 0:
            Trade.price_tracing_order(status[0]['side'].lower(), status[0]['executed_size'])
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
        else:
            self.order_side = ''
            self.order_id = ''
            self.order_price = 0
            self.order_size = 0
            self.order_status = ''

    def check_execution(self):
        status = Trade.get_order_status(self.order_id)
        if len(status) > 0:
            self.order_size = status[0]['outstanding_size']
            self.posi_side = status[0]['side'].lower()
            self.posi_price = status[0]['average_price']
            self.posi_size = status[0]['executed_size']
            self.posi_status = 'partially executed'
            if self.order_size == 0:
                self.order_side = ''
                self.order_id = ''
                self.order_price = 0
                self.order_size = 0
                self.order_status = ''
                self.posi_status = 'fully executed'
        else: #order has been expired
            self.order_side = ''
            self.order_id = ''
            self.order_price = 0
            self.order_size = 0
            self.order_status = ''
            print('order has been expired')


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








    def start_xgb_bot(self):
        model = XgbModel()
        print('bot - updating crypto data..')                               #update crypto data for initial calc
        CryptowatchDataGetter.initialize_for_bot()
        print('bot - initializing MarketData2..')  # update crypto data for initial calc
        MarketData2.initialize(110,30,500)
        print('bot - generating training data..')
        df = MarketData2.generate_df(MarketData2.ohlc_bot)             #genrate df for initial xgb training
        train_x, test_x, train_y, test_y = model.generate_data(copy.deepcopy(df), 1)
        print('bot - training xgb model..')
        bst = model.train(train_x, train_y)                                 #initial xgb training
        print('bot - training completed..')
        prediction = []
        while SystemFlg.get_system_flg():                                   #main loop for bot
            if datetime.now().second == 1:
                res, omd = CryptowatchDataGetter.bot_data_update(datetime.now(),MarketData2.ohlc_bot,copy.deepcopy(df))
                if res == 0:

                    MarketData2.update_ohlc_index_for_bot(omd)
                    df = MarketData2.generate_df_for_bot(MarketData2.ohlc_bot)
                    train_x = model.generate_bot_train_data(copy.deepcopy(df))
                    prediction = bst.predict(xgb.DMatrix(train_x))
                    omd = MarketData2.ohlc_bot

                    print('dt={}, open={}, high={}, low={}, close={}, pre={}'.foramt(omd.dt[len(omd)-1], omd.open[len(omd.open)-1],
                                                                                     omd.high[len(omd.high)-1],
                                                                                     omd.low[len(omd.low)-1],
                                                                                     omd.close[len(omd.close)-1],
                                                                                     prediction[0]
                                                                                     ))
            time.sleep(0.5)

if __name__ == '__main__':
    SystemFlg.initialize()
    bot = Bot()
    bot.start_bot()





