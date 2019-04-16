import threading
import xgboost as xgb
import pandas as pd
import time
import copy
import pickle
from catboost import Pool
from SystemFlg import SystemFlg
from CatModel import CatModel
from datetime import timedelta
from MarketData2 import MarketData2
from CryptowatchDataGetter import CryptowatchDataGetter
from LogMaster import LogMaster
from Trade import Trade
from datetime import datetime
#import datetime
import pytz


'''
現状price tracing order時にplがずれるので、最初にaccount data get and check diff from initialize deposit as a account pl
bot開始時に現在のholdingを確認して、それをbot posiに反映させて開始する
厳密にupdate indexの計算の検証
write log to csv
ローソク足チャートにentry point, plなど表示
daily maintenanceの時にMarketData, Tradeなどinitialize。（理想的には、colabで最新データ使ってtrainingして、学習済みmodelをdownload
'''

'''
長期で下落が見込まれる状況でも決まった時間のfuture sideだけで取引するとリスクに見合わないトレードになってしまうことがありうる
ボラを新しい特徴として入れる代わりに、max termのwindowを広げることでoverfitを減らせる？  
plが近づいた時にpredictが同じ方向だったら利確しない方が合理的？
ポジ持ってる時に3(both)になったら一旦exitするのが安全？plにはどう影響する？
'''
class Bot:
    def initialize(self,pl_kijun):
        self.pl_kijun = pl_kijun
        self.posi_initialzie()
        self.order_initailize()
        self.pl = 0
        self.holding_pl = 0
        self.pl_log = []
        self.num_trade = 0
        self.num_win = 0
        self.win_rate = 0
        self.margin_rate = 120.0
        self.leverage = 15.0

    def posi_initialzie(self):
        self.posi_side = ''
        self.posi_id = ''
        self.posi_price = 0
        self.posi_size = 0
        self.posi_status = ''

    def order_initailize(self):
        self.order_side = ''
        self.order_id = ''
        self.order_price = 0
        self.order_size = 0
        self.order_status = ''
        self.order_dt = ''


    def calc_opt_size(self):
        collateral = Trade.get_collateral()['collateral']
        #price * size * 1/0.15 = margin
        #110 = price * size * 1/0.15 / current_asset
        size = round((1.5 * collateral * self.margin_rate) / Trade.get_last_price() * 1.0/self.leverage,2)
        return size
        #return round((self.leverage * (current_asset / Trade.get_last_price()) * 100.0) / self.margin_rate,2)

    def calc_and_log_pl(self, ave_p, size):
        pl = (ave_p - self.posi_price) * self.posi_size if self.posi_side == 'buy' else (self.posi_price - ave_p) * self.posi_size
        self.pl += round(pl,2)
        self.pl_log.append(self.pl)
        self.num_trade += 1
        if pl > 0:
            self.num_win += 1
        self.win_rate = round(float(self.num_win) / float(self.num_trade),2)
        print('pl = {}, num = {}, win_rate = {}'.format(self.pl, self.num_trade, self.win_rate))

    def calc_holding_pl(self):
        lastp = Trade.get_last_price()
        self.holding_pl = round((lastp - self.posi_price) * self.posi_size if self.posi_side == 'buy' else (self.posi_price - lastp) * self.posi_size ,2)

    def entry_order(self, side, price, size):
        res = Trade.order(side, price, size, 1)
        if len(res) > 10:
            self.order_id = res
            self.order_side = side
            self.order_price = price
            self.order_size = size
            self.order_status = 'new boarding'
            self.order_dt = datetime.now()
            LogMaster.add_log({'dt':self.order_dt,'action_message':'new entry for '+side+' @'+str(price)+' x'+str(size)})
            print('new entry: side = {}, price = {}, size = {}'.format(side, price, size))
        else:
            LogMaster.add_log({'dt': self.order_dt, 'action_message': 'failed new entry for ' + side + ' @' + str(price) + ' x' + str(size)})
            print('order failed!')
            print('posi_side={}, posi_size={}, order_side={}, order_size={}, order_status={}'.format(self.posi_side,self.posi_size,self.order_side,self.order_size,self.order_status))

    def pl_order(self):
        side = 'buy' if self.posi_side == 'sell' else 'sell'
        price = self.posi_price + self.pl_kijun if self.posi_side == 'buy' else self.posi_price - self.pl_kijun
        res = Trade.order(side, price, self.posi_size, 1440)
        if len(res) > 10:
            self.order_id = res
            self.order_side = side
            self.order_price = price
            self.order_size = self.posi_size
            self.order_status = 'pl ordering'
            self.order_dt = datetime.now()
            print('pl order: side = {}, price = {}, size = {}'.format(self.order_side, self.order_price, self.order_size))
            LogMaster.add_log({'dt': self.order_dt, 'action_message': 'pl entry for ' + side + ' @' + str(price) + ' x' + str(self.posi_size)})
        else:
            LogMaster.add_log({'dt': self.order_dt,'action_message': 'failed pl entry!'})
            print('failed pl order!')


    def exit_order(self):
        print('exit order')
        res = Trade.cancel_and_wait_completion(self.order_id) #cancel pl order
        if len(res) > 0:
            self.posi_size = self.posi_size - res[0]['executed_size']
        if self.posi_size > 0:
            side = 'buy' if self.posi_side == 'sell' else 'sell'
            ave_p = Trade.price_tracing_order(side, self.posi_size)
            if ave_p != '': #completed price tracing order
                self.calc_and_log_pl(ave_p, self.posi_size)
                LogMaster.add_log({'dt': datetime.now(), 'action_message': 'exit completed ave_price='+str(ave_p)+' x'+str(self.posi_size)})
                self.posi_initialzie()
                self.order_initailize()
            else:
                LogMaster.add_log({'dt': datetime.now(),'action_message': 'Reached API access limitation!'})
                print('Reached API access limitation!')
                print('Sleep for 60s...')
                time.sleep(60)
                print('Resumed from API limitation sleep.')
        else:
            print('order has been fully executed before cancellation')
            self.calc_and_log_pl(res[0]['average_price'], res[0]['executed_size'])
            LogMaster.add_log({'dt': datetime.now(),'action_message': 'exit - order has been fully executed before cancellation' + str(res[0]['average_price']) + ' x' + str(res[0]['executed_size'])})
            self.posi_initialzie()
            self.order_initailize()


    def cancel_order(self):
        print('cancel order')
        status = Trade.cancel_and_wait_completion(self.order_id)
        if len(status) > 0:
            print('cancel failed, partially executed')
            ave_p = Trade.price_tracing_order(status[0]['side'].lower(), status[0]['executed_size'])
            self.calc_and_log_pl(ave_p, status[0]['executed_size'])
            LogMaster.add_log({'dt': datetime.now(),'action_message': 'cancel order - cancel failed and partially executed. closed position.' + str(ave_p) + ' x' + str(status[0]['executed_size'])})
            self.posi_initialzie()
            self.order_initailize()
        else:
            LogMaster.add_log({'dt': datetime.now(), 'action_message':'cancelled order'})
            self.order_initailize()

    def check_execution(self):
        status = Trade.get_order_status(self.order_id)
        if len(status) > 0:
            if status[0]['outstanding_size'] == 0 and 'pl' in self.order_status: #pl is fully executed
                print(status[0])
                self.calc_and_log_pl(status[0]['average_price'], status[0]['executed_size'])
                LogMaster.add_log({'dt': datetime.now(), 'action_message':'pl order has been fully executed.'+'ave_price='+str(status[0]['average_price'])+' size='+str(status[0]['executed_size'])})
                self.order_initailize()
                self.posi_initialzie()
                print('pl order has been fully executed')
            else:
                if status[0]['outstanding_size'] == 0: #new entry has been fully executed
                    print('entry order has been fully executed')
                    self.order_initailize()
                    self.posi_side = status[0]['side'].lower()
                    self.posi_price = status[0]['average_price']
                    self.posi_size = status[0]['executed_size']
                    self.posi_status = 'fully executed'
                    print('current position: side = {}, price = {}, size = {}'.format(self.posi_side, self.posi_price, self.posi_size))
                    LogMaster.add_log({'dt': datetime.now(), 'action_message':'entry order has been fully executed'})
                elif status[0]['executed_size'] > self.posi_size: #entry order has been partially executed
                    print('entry order partially executed')
                    self.order_size = status[0]['executed_size']
                    self.order_status = 'partially executed'
                    self.posi_status = 'partially executed'
                    self.posi_side = status[0]['side'].lower()
                    self.posi_price = status[0]['average_price']
                    self.posi_size = status[0]['executed_size']
                    LogMaster.add_log({'dt': datetime.now(), 'action_message': 'entry order partially executed.'+'price='+str(status[0]['average_price'])+' size='+str(status[0]['executed_size'])})
                    print('current position: side = {}, price = {}, size = {}'.format(self.posi_side, self.posi_price,
                                                                                      self.posi_size))
                elif status[0]['child_order_state'] == 'ACTIVE' and 'boarded' not in self.order_status:
                    print('order has been boarded')
                    self.order_status = 'new boarded' if self.order_status == 'new boarding' else 'pl boarded'

        elif (datetime.now() - self.order_dt).total_seconds() >= 60: #order has been expired
            self.order_initailize()
            print('order has been expired')
        else:
            print('order is not yet boarded')  # maybe order is not yet boarded
            pass


    def start_bot(self,pl_kijun):
        self.initialize(pl_kijun)
        Trade.cancel_all_orders()
        print('bot - updating crypto data..')
        LogMaster.add_log({'action_message':'bot - updating crypto data..'})
        CryptowatchDataGetter.get_and_add_to_csv()
        print('bot - initializing MarketData2..')
        LogMaster.add_log({'action_message': 'bot - initializing MarketData2..'})
        MarketData2.initialize_from_bot_csv(110, 100, 900)
        train_df = MarketData2.generate_df(MarketData2.ohlc_bot)
        #print(train_df)
        #model = XgbModel()
        model = CatModel()
        print('bot - training xgb model..')
        LogMaster.add_log({'action_message': 'bot - training xgb model..'})
        train_x, test_x, train_y, test_y = model.generate_data(train_df, 1)
        #print('x shape '+str(train_x.shape))
        #print('y shape '+str(train_y.shape))
        #bst = model.train(train_x, train_y)
        bst = model.read_dump_model('./cat_model.dat')
        print('bot - training completed..')
        print('bot - updating crypto data..')
        LogMaster.add_log({'action_message': 'bot - training completed..'})
        #CryptowatchDataGetter.get_and_add_to_csv()
        #MarketData2.initialize_from_bot_csv(110, 100, 900)
        MarketData2.ohlc_bot.cut_data(1000)
        print('bot - started bot loop.')
        LogMaster.add_log({'action_message': 'bot - started bot loop.'})
        predict = [0]
        JST = pytz.timezone('Asia/Tokyo')
        start = time.time()
        while SystemFlg.get_system_flg():
            while datetime.now(tz=JST).hour == 3 and datetime.now(tz=JST).minute >= 50:
                time.sleep(10) #wait for daily system maintenace
            if datetime.now(tz=JST).second == 1 or datetime.now(tz=JST).second == 2:
                elapsed_time = time.time() - start
                print("bot elapsed_time:{0}".format(round(elapsed_time/60,2)) + "[min]")
                print('private access per min={}, num private access={}, num public access={}'.format(Trade.num_private_access_per_min, Trade.num_private_access, Trade.num_public_access))
                res, omd = CryptowatchDataGetter.get_data_after_specific_ut(MarketData2.ohlc_bot.unix_time[-1])
                #print('downloaded data - '+str(datetime.now(tz=JST)))
                if res == 0:
                    for i in range(len(omd.dt)):
                        MarketData2.ohlc_bot.add_and_pop(omd.unix_time[i],omd.dt[i], omd.open[i], omd.high[i], omd.low[i], omd.close[i], omd.size[i])
                        #print('add and pop MarketData - ' + str(datetime.now(tz=JST)))
                    #print('updated -start MarketData - ' + str(datetime.now(tz=JST)))
                    MarketData2.update_ohlc_index_for_bot2()
                    #print('updated -end MarketData - ' + str(datetime.now(tz=JST)))
                    df = MarketData2.generate_df_for_bot(MarketData2.ohlc_bot)
                    pred_x = model.generate_bot_pred_data(df)
                    #print('generated df - ' + str(datetime.now(tz=JST)))
                    # predict = bst.predict(xgb.DMatrix(pred_x))
                    predict = bst.predict(Pool(pred_x))
                    #print('predicted - ' + str(datetime.now(tz=JST)))
                    LogMaster.add_log({'dt':MarketData2.ohlc_bot.dt[-1],'open':MarketData2.ohlc_bot.open[-1],'high':MarketData2.ohlc_bot.high[-1],
                                      'low':MarketData2.ohlc_bot.low[-1],'close':MarketData2.ohlc_bot.close[-1],'posi_side':self.posi_side,
                                       'posi_price':self.posi_price,'posi_size':self.posi_size,'order_side':self.order_side,'order_price':self.order_price,
                                       'order_size':self.order_size,'num_private_access':Trade.num_private_access, 'num_public_access':Trade.num_public_access,
                                       'num_private_per_min':Trade.num_private_access_per_min,'num_trade':self.num_trade,'win_rate':self.win_rate,
                                       'prediction':predict[0]})
                    print('dt={}, close={}, predict={}, pl={}, num_trade={}, win_rate={}, posi_side={}, posi_price={}, order_side={}, order_price={}'.format(MarketData2.ohlc_bot.dt[-1],
                                                                        MarketData2.ohlc_bot.close[-1],
                                                                                                 predict[0],
                                                                                                 self.pl+self.holding_pl,
                                                                                                 self.num_trade,
                                                                                                 self.win_rate, self.posi_side, self.posi_price, self.order_side, self.order_price))
                else:
                    print('crypto watch data download error!')
            if self.posi_side == '' and self.order_side == '': #no position no order
                if predict[0] == 1:
                    self.entry_order('buy', MarketData2.ohlc_bot.close[-1], self.calc_opt_size())
                elif predict[0] == 2:
                    self.entry_order('sell', MarketData2.ohlc_bot.close[-1], self.calc_opt_size())
            elif self.posi_side == '' and self.order_side != '': #no position and ordering
                if (self.order_side == 'buy' and (predict[0] == 2 or predict[0] == 0)) or (self.order_side == 'sell' and (predict[0] == 1 or predict[0] == 0)):
                    self.cancel_order()
            elif self.posi_side != '' and self.order_side == '': #holding position and no order
                self.pl_order()
            elif self.posi_side == 'buy' and (predict[0] == 2 or predict[0] == 0) or self.posi_side == 'sell' and (predict[0] == 1 or predict[0] == 0): #exit when oposit predict
                self.exit_order()
            elif self.posi_side != '':
                self.calc_holding_pl()
            if self.order_side != '':
                self.check_execution()
            time.sleep(0.5)




if __name__ == '__main__':
    SystemFlg.initialize()
    Trade.initialize()
    LogMaster.initialize()
    bot = Bot()
    bot.start_bot(900)





