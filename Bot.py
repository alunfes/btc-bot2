import threading
import xgboost as xgb
import pandas as pd
import time
import copy
import pickle
from catboost import Pool
from SystemFlg import SystemFlg
from CatModel import CatModel
from XgbModel import  XgbModel
from datetime import timedelta
from MarketData2 import MarketData2
from CryptowatchDataGetter import CryptowatchDataGetter
from LogMaster import LogMaster
from LineNotification import LineNotification
from Trade import Trade
from datetime import datetime
import datetime as dt
#import datetime
import pytz


'''
catboost classifierの識別の確率など取れるのか確認。
pl直後にpredictionにしたがってエントリーするsimだと、最適なfuture periodとkijungが違うかも。
現状price tracing order時にplがずれるので、最初にaccount data get and check diff from initialize deposit as a account pl
bot開始時に現在のholdingを確認して、それをbot posiに反映させて開始する
厳密にupdate indexの計算の検証
ローソク足チャートにentry point, plなど表示
daily maintenanceの時にMarketData, Tradeなどinitialize。（理想的には、colabで最新データ使ってtrainingして、学習済みmodelをdownload
'''

'''
長期で下落が見込まれる状況でも決まった時間のfuture sideだけで取引するとリスクに見合わないトレードになってしまうことがありうる
ボラを新しい特徴として入れる代わりに、max termのwindowを広げることでoverfitを減らせる？  
plが近づいた時にpredictが同じ方向だったら利確しない方が合理的？
ポジ持ってる時に3(both)になったら一旦exitするのが安全？plにはどう影響する？
pred=3で大きなボラで損が広がる時は損切りするようにした方が良いかもしれない。
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
        self.initial_asset = Trade.get_collateral()
        self.JST = pytz.timezone('Asia/Tokyo')
        Trade.cancel_all_orders()
        time.sleep(5)
        self.sync_position_order()



    def combine_status_data(self, status):
        side = ''
        size = 0
        price = 0
        for s in status:
            side = s['side'].lower()
            size += float(s['size'])
            price += float(s['price']) * float(s['size'])
        price = round(price / size)
        return side, round(size,2), round(price)

    def sync_position_order(self):
        position = Trade.get_positions()
        orders = Trade.get_orders()
        if len(position) > 0:
            posi_side, posi_size, posi_price = self.combine_status_data(position)
            if self.posi_side != posi_side or self.posi_price!=posi_price or self.posi_size != posi_size:
                print('position unmatch was detected! Synchronize with account position data.')
                print('posi_side={},posi_price={},posi_size={}'.format(self.posi_side,self.posi_price,self.posi_size))
                print(position)
            self.posi_side, self.posi_size, self.posi_price = posi_side, posi_size, posi_price
            self.posi_status = 'fully executed'
            print('synchronized position data, side='+str(self.posi_side)+', size='+str(self.posi_size)+', price='+str(self.posi_price))
        else:
            self.posi_initialzie()
        if len(orders) > 0:#need to update order status
            if len(orders) > 1:
                print('multiple orders are found! Only the first one will be synchronized!')
            self.order_id = orders[0]['info']['child_order_acceptance_id']
            self.order_side = orders[0]['info']['side'].lower()
            self.order_size = float(orders[0]['info']['size'])
            self.order_price = round(float(orders[0]['info']['price']))
            print('synchronized order data, side='+str(self.order_side)+', size='+str(self.order_size)+', price='+str(self.order_price))
        else:
            self.order_initailize()


    def posi_initialzie(self):
        self.posi_side = ''
        self.posi_id = ''
        self.posi_price = 0
        self.posi_size = 0
        self.posi_status = ''
        self.original_posi_size = 0

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
        #print('pl = {}, num = {}, win_rate = {}'.format(self.pl, self.num_trade, self.win_rate))

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
            self.original_posi_size = size
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
            self.original_posi_size = self.posi_size
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
        if len(status) == 0: #no order info
            if self.order_status == 'pl ordering':#pl order not boarded
                print('pl order is not boarded')
                #print(Trade.get_orders())
            elif self.order_status == 'new boarding':
                print('new entry is not boarded')#new entry not boarded¥
                #print(Trade.get_orders())
            elif self.order_status == 'pl boarded':
                if self.order_dt.astimezone(tz=self.JST) + dt.timedelta(seconds=60) < datetime.now(tz=self.JST):
                    flg_check_expiration = True
                    for i in range(3):
                        time.sleep(1)
                        status = Trade.get_order_status(self.order_id)
                        if len(status) > 0:
                            flg_check_expiration = False
                            break
                    if flg_check_expiration:
                        print('pl order has been expired: ' +str(datetime.now()))
                        self.order_initailize()
                        LogMaster.add_log({'dt': datetime.now(),'action_message': 'pl order has been expired'})
            elif self.order_status == 'new boarded':
                if self.order_dt.astimezone(tz=self.JST)     + dt.timedelta(seconds=60) < datetime.now(tz=self.JST):
                    flg_check_expiration = True
                    for i in range(3):
                        time.sleep(1)
                        status = Trade.get_order_status(self.order_id)
                        if len(status) > 0:
                            flg_check_expiration = False
                            break
                    if flg_check_expiration:
                        print('new entry order has been expired: ' +str(datetime.now()))
                        self.order_initailize()
                        LogMaster.add_log({'dt': datetime.now(),'action_message': 'new entry order has been expired'})
            else:
                print('unknown status!')
        else: #order boarded or executed
            if 'pl' in self.order_status: #in case pl order
                if self.order_status == 'pl ordering':
                    self.order_status = 'pl boarded'
                    print('pl order boarded: ' +str(datetime.now()))
                if status[0]['child_order_state'] == 'COMPLETED': #pl order fully executed
                    print('pl order has been completed.'+'ave_price='+str(status[0]['average_price'])+' size='+str(status[0]['executed_size']))
                    self.calc_and_log_pl(status[0]['average_price'], status[0]['executed_size'])
                    self.sync_position_order()
                    LogMaster.add_log({'dt': datetime.now(), 'action_message':'pl order has been completed.'+'ave_price='+str(status[0]['average_price'])+' size='+str(status[0]['executed_size'])})
                else:
                    if status[0]['outstanding_size'] < self.order_size: #pl order partially executed
                        self.calc_and_log_pl(status[0]['average_price'], status[0]['executed_size'])
                        self.order_size = status[0]['outstanding_size']
                        self.order_status = 'pl order partially executed'
                        self.posi_status = 'pl order partially executed'
                        self.posi_size = self.original_posi_size - status[0]['executed_size']
                        print('pl order has been partially executed. ave_price={}, size={}'.format(status[0]['average_price'], status[0]['executed_size']))
                        LogMaster.add_log({'dt': datetime.now(),'action_message': 'pl order has been partially executed.' + 'ave_price=' + str(status[0]['average_price']) + ' size=' + str(status[0]['executed_size'])})
                        print('current position side={}, price={}, size={}'.format(self.posi_side, self.posi_price, self.posi_size))
                    else:
                        pass
            else: #in case new entry
                if self.order_status == 'new boarding':
                    self.order_status = 'new boarded'
                    print('new entry boarded: '+ str(datetime.now())) #new entry not boarded
                if status[0]['child_order_state'] == 'COMPLETED':
                    print('new entry order has been completed' + 'ave_price='+str(status[0]['average_price'])+'size='+str(status[0]['executed_size']))
                    self.sync_position_order()
                    LogMaster.add_log({'dt': datetime.now(),
                                       'action_message': 'new entry order has been partially executed.' + 'ave_price=' + str(
                                           status[0]['average_price']) + ' size=' + str(status[0]['executed_size'])})
                    print('current position: side={},price={},size={}'.format(self.posi_side, self.posi_price, self.posi_size))
                elif status[0]['child_order_state'] == 'CANCELED':
                    print('order has been canceled outside of cancel and wait completion function!')
                    print(status[0])
                else: #no change in new entry order
                    pass


    def start_bot(self,pl_kijun):
        self.initialize(pl_kijun)
        Trade.cancel_all_orders()
        print('bot - updating crypto data..')
        LogMaster.add_log({'action_message':'bot - updating crypto data..'})
        CryptowatchDataGetter.get_and_add_to_csv()
        print('bot - initializing MarketData2..')
        LogMaster.add_log({'action_message': 'bot - initializing MarketData2..'})
        MarketData2.initialize_from_bot_csv(100, 1, 30, 500)
        train_df = MarketData2.generate_df(MarketData2.ohlc_bot)
        #print(train_df)
        model = XgbModel()
        #model = CatModel()
        print('bot - training xgb model..')
        LogMaster.add_log({'action_message': 'bot - training xgb model..'})
        train_x, test_x, train_y, test_y = model.generate_data(train_df, 1)
        #print('x shape '+str(train_x.shape))
        #print('y shape '+str(train_y.shape))
        #bst = model.train(train_x, train_y)
        bst = model.read_dump_model('./xgb_model.dat')
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
            time.sleep(Trade.adjusting_sleep)
            while datetime.now(tz=self.JST).hour == 3 and datetime.now(tz=self.JST).minute >= 50:
                time.sleep(10) #wait for daily system maintenace
                self.cancel_order()
                self.exit_order()
                SystemFlg.set_system_flg(False)
                break
            if datetime.now(tz=self.JST).second <= 3:
                self.sync_position_order()
                elapsed_time = time.time() - start
                print("bot elapsed_time:{0}".format(round(elapsed_time/60,2)) + "[min]")
                print('private access per min={}, num private access={}, num public access={}'.format(Trade.num_private_access_per_min, Trade.num_private_access, Trade.num_public_access))
                res, omd = CryptowatchDataGetter.get_data_after_specific_ut(MarketData2.ohlc_bot.unix_time[-1])
                #print('downloaded data - '+str(datetime.now(tz=JST)))
                if res == 0:
                    for i in range(len(omd.dt)):
                        MarketData2.ohlc_bot.add_and_pop(omd.unix_time[i],omd.dt[i], omd.open[i], omd.high[i], omd.low[i], omd.close[i], omd.size[i])
                    MarketData2.update_ohlc_index_for_bot2()
                    df = MarketData2.generate_df_for_bot(MarketData2.ohlc_bot)
                    pred_x = model.generate_bot_pred_data(df)
                    predict = bst.predict(xgb.DMatrix(pred_x))
                    LineNotification.send_notification()
                    #predict = bst.predict(Pool(pred_x))
                    #print('predicted - ' + str(datetime.now(tz=JST)))
                    LogMaster.add_log({'dt':MarketData2.ohlc_bot.dt[-1],'open':MarketData2.ohlc_bot.open[-1],'high':MarketData2.ohlc_bot.high[-1],
                                      'low':MarketData2.ohlc_bot.low[-1],'close':MarketData2.ohlc_bot.close[-1],'posi_side':self.posi_side,
                                       'posi_price':self.posi_price,'posi_size':self.posi_size,'order_side':self.order_side,'order_price':self.order_price,
                                       'order_size':self.order_size,'num_private_access':Trade.num_private_access, 'num_public_access':Trade.num_public_access,
                                       'num_private_per_min':Trade.num_private_access_per_min,'num_trade':self.num_trade,'win_rate':self.win_rate, 'pl':self.pl+self.holding_pl,
                                       'prediction':predict[0]})
                    print('dt={}, close={}, predict={}, pl={}, num_trade={}, win_rate={}, posi_side={}, posi_price={}, posi_size={}, order_side={}, order_price={}, order_size={}'.format(MarketData2.ohlc_bot.dt[-1],
                                                                        MarketData2.ohlc_bot.close[-1],
                                                                                                 predict[0],
                                                                                                 self.pl+self.holding_pl,
                                                                                                 self.num_trade,
                                                                                                 self.win_rate, self.posi_side, self.posi_price, self.posi_size, self.order_side, self.order_price, self.order_size))
                else:
                    print('crypto watch data download error!')
            if self.posi_side == '' and self.order_side == '': #no position no order
                if predict[0] == 1:
                    self.entry_order('buy', Trade.get_last_price(), self.calc_opt_size())
                elif predict[0] == 2:
                    self.entry_order('sell', Trade.get_last_price(), self.calc_opt_size())
            elif self.posi_side == '' and self.order_side != '': #no position and ordering
                if (self.order_side == 'buy' and self.posi_side=='' and (predict[0] == 2)) or (self.order_side == 'sell' and self.posi_side =='' and (predict[0] == 1)):#ノーポジでオーダーが判定を逆の時にキャンセル。
                    self.cancel_order()
            elif self.posi_side != '' and self.order_side == '': #holding position and no order
                self.pl_order()
            elif self.posi_side == 'buy' and (predict[0] == 2) or self.posi_side == 'sell' and (predict[0] == 1): # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。。
                self.exit_order()
                if self.order_status == 'pl ordering':
                    self.cancel_order()
            elif self.posi_side != '':
                self.calc_holding_pl()
            if self.order_side != '':
                self.check_execution()
            time.sleep(1)




if __name__ == '__main__':
    SystemFlg.initialize()
    Trade.initialize()
    LogMaster.initialize()
    LineNotification.initialize()
    bot = Bot()
    bot.start_bot(500)





