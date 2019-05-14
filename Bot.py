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
from WebsocketMaster import TickData
from LogMaster import LogMaster
from LineNotification import LineNotification
from Trade import Trade
from datetime import datetime
import datetime as dt
import math
#import datetime
import pytz
from numba import jit


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
    @jit
    def initialize(self,pl_kijun):
        self.pl_kijun = pl_kijun
        self.posi_initialzie()
        self.order_initailize()
        self.initial_collateral = Trade.get_collateral()['collateral']
        self.collateral_change = 0
        self.collateral_change_per_min = 0
        self.pl = 0
        self.holding_pl = 0
        self.pl_log = []
        self.num_trade = 0
        self.num_win = 0
        self.win_rate = 0
        self.pl_per_min = 0
        self.elapsed_time = 0
        self.margin_rate = 120.0
        self.leverage = 15.0
        self.initial_asset = Trade.get_collateral()
        self.JST = pytz.timezone('Asia/Tokyo')
        self.num_train_model = 0
        self.last_train_model_dt = None
        self.model = None
        self.cbm = None
        self.model_lock = threading.Lock()
        Trade.cancel_all_orders()
        time.sleep(5)
        self.sync_position_order()

    def set_model_cbm(self, model, cbm):
        with self.model_lock:
            self.model = model
            self.cbm = cbm

    def get_model_cbm(self):
        with self.model_lock:
            return (self.model, self.cbm)

    @jit
    def combine_status_data(self, status):
        side = ''
        size = 0
        price = 0
        for s in status:
            side = s['side'].lower()
            size += float(s['size'])
            price += float(s['price']) * float(s['size'])
        price = round(price / size)
        return side, round(size,8), round(price)

    def sync_position_order(self):
        position = Trade.get_positions()
        orders = Trade.get_orders()
        if len(position) > 0:
            posi_side, posi_size, posi_price = self.combine_status_data(position)
            if self.posi_side != posi_side or abs(self.posi_price - posi_price) >= 1 or abs(self.posi_size - posi_size) >= 0.01:
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
            try:
                self.order_id = orders[0]['info']['child_order_acceptance_id']
                self.order_side = orders[0]['info']['side'].lower()
                self.order_size = float(orders[0]['info']['size'])
                self.order_price = round(float(orders[0]['info']['price']))
                print('synchronized order data, side='+str(self.order_side)+', size='+str(self.order_size)+', price='+str(self.order_price))
            except Exception as e:
                print('Bot-sync_position_order:sync order key error!')
                LogMaster.add_log({'dt': datetime.now(),'api_error': 'Bot-sync_position_order:sync order key error!'})
        else:
            self.order_initailize()

    @jit
    def posi_initialzie(self):
        self.posi_side = ''
        self.posi_id = ''
        self.posi_price = 0
        self.posi_size = 0
        self.posi_status = ''
        self.original_posi_size = 0

    @jit
    def order_initailize(self):
        self.order_side = ''
        self.order_id = ''
        self.order_price = 0
        self.order_size = 0
        self.order_status = ''
        self.order_dt = ''

    @jit
    def calc_opt_size(self):
        collateral = Trade.get_collateral()['collateral']
        if TickData.get_1m_std() > 10000:
            multiplier = 0.5
            print('changed opt size multiplier to 0.5')
            LogMaster.add_log({'dt': self.order_dt,
                               'action_message': 'changed opt size multiplier to 0.5'})
            LineNotification.send_error('changed opt size multiplier to 0.5')
        else:
            multiplier = 1.5
        #size = round((multiplier * collateral * self.margin_rate) / Trade.get_last_price() * 1.0/self.leverage,2)
        size = round((multiplier * collateral * self.margin_rate) / TickData.get_ltp() * 1.0 / self.leverage, 2)
        return size

    @jit
    def calc_opt_pl(self):
        if TickData.get_1m_std() > 10000:
            newpl = self.pl_kijun * math.log((TickData.get_1m_std() / 100000)) + 5
            print('changed opt pl kijun to '+str(newpl))
            LogMaster.add_log({'dt': self.order_dt,
                               'action_message': 'changed opt pl kijun to '+str(newpl)})
            LineNotification.send_error('changed opt pl kijun to '+str(newpl))
            return newpl
        else:
            return self.pl_kijun

    @jit
    def calc_and_log_pl(self, ave_p, size):
        pl = (ave_p - self.posi_price) * self.posi_size if self.posi_side == 'buy' else (self.posi_price - ave_p) * self.posi_size
        self.pl += round(pl)
        self.pl_log.append(round(self.pl))
        self.num_trade += 1
        if pl > 0:
            self.num_win += 1
        self.win_rate = round(float(self.num_win) / float(self.num_trade),2)
        if self.elapsed_time >0:
            self.pl_per_min = round( (self.pl + self.holding_pl) / (self.elapsed_time /60.0),4)
        else:
            pass

    @jit
    def calc_collateral_change(self):
        col = Trade.get_collateral()
        self.collateral_change = round(float(col['collateral']) + float(col['open_position_pnl']) - self.initial_collateral)
        if self.elapsed_time > 0:
            self.collateral_change_per_min = round(self.collateral_change / (self.elapsed_time/60.0), 4)
        else:
            pass

    @jit
    def calc_holding_pl(self):
        lastp = TickData.get_ltp()
        #lastp = Trade.get_last_price()
        #lastp = Trade.get_current_price()
        self.holding_pl = round((lastp - self.posi_price) * self.posi_size if self.posi_side == 'buy' else (self.posi_price - lastp) * self.posi_size)


    @jit
    def entry_order(self, side, price, size):
        res = Trade.order(side, price, size, 'limit', 15)
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

    @jit
    def entry_market_order(self, side, price, size):
        res = Trade.order(side, price, size, 'market', 1)
        if len(res) > 10:
            self.order_id = res
            self.order_side = side
            self.order_price = price
            self.order_size = size
            self.original_posi_size = size
            self.order_status = 'new boarding'
            self.order_dt = datetime.now()
            LogMaster.add_log({'dt': self.order_dt, 'action_message': 'new market order entry for ' + side + ' @' + str(price) + ' x' + str(size)})
            print('new market order entry: side = {}, price = {}, size = {}'.format(side, price, size))
        else:
            LogMaster.add_log({'dt': self.order_dt,'action_message': 'failed new market order entry for ' + side + ' @' + str(price) + ' x' + str(size)})
            print('order failed!')
            print('posi_side={}, posi_size={}, order_side={}, order_size={}, order_status={}'.format(self.posi_side,
                                                                                                     self.posi_size,
                                                                                                     self.order_side,
                                                                                                     self.order_size,
                                                                                                     self.order_status))

    @jit
    def entry_price_tracing_order(self, side, size):
        ave_p = Trade.price_tracing_order(side, size)
        if ave_p != '':
            LogMaster.add_log({'dt': datetime.now(),
                               'action_message': 'new entry for ' + side + ' @'+str(ave_p) + ' x' + str(self.posi_size)})
        else:  #
            LogMaster.add_log({'dt': datetime.now(), 'action_message': 'Reached API access limitation!'})
            print('Reached API access limitation!')
            print('Sleep for 60s...')
            time.sleep(60)
            print('Resumed from API limitation sleep.')



    @jit
    def pl_order(self):
        side = 'buy' if self.posi_side == 'sell' else 'sell'
        pl_kijun = self.calc_opt_pl()
        price = self.posi_price + pl_kijun if self.posi_side == 'buy' else self.posi_price - pl_kijun
        res = Trade.order(side, price, self.posi_size, 'limit', 1440)
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


    @jit
    def exit_order(self):
        print('exit order')
        res = Trade.cancel_and_wait_completion(self.order_id) #cancel pl order
        if len(res) > 0:
            self.posi_size = self.posi_size - res['executed_size']
        if self.posi_size > 0:
            side = 'buy' if self.posi_side == 'sell' else 'sell'
            ave_p = Trade.price_tracing_order(side, self.posi_size)
            if ave_p != '': #completed price tracing order
                self.calc_and_log_pl(ave_p, self.posi_size)
                LogMaster.add_log({'dt': datetime.now(), 'action_message': 'exit completed ave_price='+str(ave_p)+' x'+str(self.posi_size)})
                self.posi_initialzie()
                self.order_initailize()
            else: #
                LogMaster.add_log({'dt': datetime.now(),'action_message': 'Reached API access limitation!'})
                print('Reached API access limitation!')
                print('Sleep for 60s...')
                time.sleep(60)
                print('Resumed from API limitation sleep.')
        else:
            print('order has been fully executed before cancellation')
            self.calc_and_log_pl(res['average_price'], res['executed_size'])
            LogMaster.add_log({'dt': datetime.now(),'action_message': 'exit - order has been fully executed before cancellation' + str(res['average_price']) + ' x' + str(res['executed_size'])})
            self.posi_initialzie()
            self.order_initailize()


    @jit
    def cancel_order(self):
        print('cancel order')
        status = Trade.cancel_and_wait_completion(self.order_id)
        if len(status) > 0:
            print('cancel failed, partially executed')
            ave_p = Trade.price_tracing_order(status['side'].lower(), status['executed_size'])
            self.calc_and_log_pl(ave_p, status['executed_size'])
            LogMaster.add_log({'dt': datetime.now(),'action_message': 'cancel order - cancel failed and partially executed. closed position.' + str(ave_p) + ' x' + str(status['executed_size'])})
            self.posi_initialzie()
            self.order_initailize()
        else:
            LogMaster.add_log({'dt': datetime.now(), 'action_message':'cancelled order'})
            self.order_initailize()


    def check_execution(self):
        status = Trade.get_order_status(self.order_id)
        if status is not None:
            if len(status) == 0: #no order info
                if self.order_status == 'pl ordering':#pl order not boarded
                    print('pl order is not boarded')
                    #print(Trade.get_orders())
                elif self.order_status == 'new boarding':
                    print('new entry is not boarded')#new entry not boarded¥
                    #print(Trade.get_orders())
                elif self.order_status == 'pl boarded':
                    if self.order_dt.astimezone(tz=self.JST) + dt.timedelta(seconds=60) < datetime.now(tz=self.JST):
                        orders = Trade.get_orders()
                        if len(orders) > 0:
                            try:
                                self.order_id = orders[0]['child_order_acceptance_id']
                                print('pl order id has been updates due to unknown error!')
                                LogMaster.add_log(
                                    {'dt': datetime.now(),
                                     'api_error': 'pl order id has been updates due to unknown error!'})
                            except Exception as e:
                                print('Bot - check_execution:key error was detected!')
                                print(orders)
                                LogMaster.add_log(
                                    {'dt': datetime.now(),
                                     'api_error': 'Bot - check_execution:key error was detected!'})

                        else:
                            print('pl order can not be found!')
                            LogMaster.add_log(
                                {'dt': datetime.now(),
                                 'api_error': 'pl order can not be found!'})

                    '''
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
                    '''
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
        else:
            print('order status is not available due to API access limitation')
            pass

    @jit
    def check_and_train_model(self, num_term, window_term, future_period, pl_kijun):
        print(str(datetime.now(tz=self.JST)) + ' - Training Model...')
        LineNotification.send_error(str(datetime.now(tz=self.JST)) + ' - Training Model...')
        start = time.time()
        self.last_train_model_dt = time.time()
        CryptowatchDataGetter.get_and_add_to_csv()
        MarketData2.initialize_from_bot_csv(num_term, window_term, future_period, pl_kijun)
        newmodel = CatModel()
        train_df = MarketData2.generate_df(MarketData2.ohlc_bot)
        train_x, test_x, train_y, test_y = newmodel.generate_data(train_df, 0)
        cbm = newmodel.train(train_x, train_y)
        elapsed_time = time.time() - start
        print('Elapsed time='+str(round(elapsed_time/60.0,2))+' - completed training model.')
        LineNotification.send_error('Completed model training. '+'Elapsed time='+str(round(elapsed_time/60.0,2)))
        self.set_model_cbm(newmodel,cbm)

    @jit
    def start_bot(self,pl_kijun, future_period, num_term, window_term):
        self.initialize(pl_kijun)
        Trade.cancel_all_orders()
        print('bot - updating crypto data..')
        LogMaster.add_log({'action_message':'bot - updating crypto data..'})
        CryptowatchDataGetter.get_and_add_to_csv()
        print('bot - initializing MarketData2..')
        LogMaster.add_log({'action_message': 'bot - initializing MarketData2..'})
        MarketData2.initialize_from_bot_csv(num_term, window_term, future_period, pl_kijun, 5000)
        print('bot - starting websocket...')
        TickData.initialize()
        time.sleep(5)
        #train_df = MarketData2.generate_df(MarketData2.ohlc_bot)
        #print(train_df)
        #model = XgbModel()
        model = CatModel()
        print('bot - generating training data')
        LogMaster.add_log({'action_message': 'bot - training xgb model..'})
        #train_x, test_x, train_y, test_y = model.generate_data(train_df, 1)
        print('bot - training model..')
        #bst = xgb.Booster()  # init model
        #bst.load_model('./Model/bst_model.dat')
        cbm = model.read_dump_model('./Model/cat_model.dat')
        self.set_model_cbm(model,cbm)
        self.last_train_model_dt = time.time()
        print('bot - training completed..')
        print('bot - updating crypto data..')
        LogMaster.add_log({'action_message': 'bot - training completed..'})
        MarketData2.ohlc_bot.del_data(5000)

        print('bot - started bot loop.')
        LogMaster.add_log({'action_message': 'bot - started bot loop.'})
        predict = [0]
        JST = pytz.timezone('Asia/Tokyo')
        start = time.time()
        while SystemFlg.get_system_flg():
            #time.sleep(Trade.adjusting_sleep)
            if (datetime.now(tz=self.JST).hour == 3 and datetime.now(tz=self.JST).minute >= 48):
                print('sleep waiting for system maintenance')
                if self.posi_side == '':
                    self.cancel_order()
                time.sleep(780)  # wait for daily system maintenace
                print('resumed from maintenance time sleep')
            #elif (time.time() - self.last_train_model_dt  >= 3600 * 3): #train model every 3h with most latest data
            #    th = threading.Thread(target=self.check_and_train_model(num_term,window_term,future_period,pl_kijun))
            #    th.start()
            elif datetime.now(tz=self.JST).second <= 3:
                self.sync_position_order()
                self.elapsed_time = time.time() - start
                print("bot elapsed_time:{0}".format(round(self.elapsed_time/60,2)) + "[min]")
                print('num total access per 300s={}, num private access={}, num public access={}'.format(Trade.total_access_per_300s, Trade.num_private_access, Trade.num_public_access))
                res, omd = CryptowatchDataGetter.get_data_after_specific_ut(MarketData2.ohlc_bot.unix_time[-1])
                #print('cryptowatch completed ='+datetime.now(tz=self.JST).strftime("%H:%M:%S"))
                #print('downloaded data - '+str(datetime.now(tz=JST)))
                if res == 0:
                    for i in range(len(omd.dt)):
                        MarketData2.ohlc_bot.add_and_pop(omd.unix_time[i],omd.dt[i], omd.open[i], omd.high[i], omd.low[i], omd.close[i], omd.size[i])
                    MarketData2.update_ohlc_index_for_bot2()
                    df = MarketData2.generate_df_for_bot(MarketData2.ohlc_bot)
                    MarketData2.ohlc_bot.del_data(5000)
                    #print('MD df completed =' +datetime.now(tz=self.JST).strftime("%H:%M:%S"))
                    pred_x = self.get_model_cbm()[0].generate_bot_pred_data(df)
                    #print('Model df completed =' +datetime.now(tz=self.JST).strftime("%H:%M:%S"))
                    #predict = bst.predict(xgb.DMatrix(pred_x))
                    predict = self.get_model_cbm()[1].predict(Pool(pred_x))
                    #print('Prediction completed =' +datetime.now(tz=self.JST).strftime("%H:%M:%S"))
                    #print('predicted - ' + str(datetime.now(tz=JST)))
                    self.calc_collateral_change()
                    LogMaster.add_log({'dt':MarketData2.ohlc_bot.dt[-1],'open':MarketData2.ohlc_bot.open[-1],'high':MarketData2.ohlc_bot.high[-1],
                                      'low':MarketData2.ohlc_bot.low[-1],'close':MarketData2.ohlc_bot.close[-1],'posi_side':self.posi_side,
                                       'posi_price':self.posi_price,'posi_size':self.posi_size,'order_side':self.order_side,'order_price':self.order_price,
                                       'order_size':self.order_size,'num_private_access':Trade.num_private_access, 'num_public_access':Trade.num_public_access,
                                       'num_total_access_per_300s':Trade.total_access_per_300s,'num_trade':self.num_trade,'win_rate':self.win_rate, 'pl':self.pl+self.holding_pl,
                                       'pl_per_min':self.pl_per_min, 'prediction':predict[0], 'collateral_change':self.collateral_change,'collateral_change_per_min':self.collateral_change_per_min})
                    LineNotification.send_notification()
                    print('dt={}, close={}, predict={}, pl={}, collateral_change={}, pl_per_min={}, collateral_change_per_min={}, num_trade={}, std_1m={}, win_rate={}, posi_side={}, posi_price={}, posi_size={}, order_side={}, order_price={}, order_size={}'
                          .format(MarketData2.ohlc_bot.dt[-1],MarketData2.ohlc_bot.close[-1],predict[0],self.pl+self.holding_pl, self.collateral_change, self.pl_per_min, self.collateral_change_per_min,
                                  self.num_trade, TickData.get_1m_std(), self.win_rate, self.posi_side, self.posi_price, self.posi_size, self.order_side, self.order_price, self.order_size))
                else:
                    print('crypto watch data download error!')
            if self.posi_side == '' and self.order_side == '': #no position no order
                if predict[0] == 1:
                    self.entry_order('buy', TickData.get_bid_price() + 1, self.calc_opt_size())
                    #self.entry_order('buy', Trade.get_bid_price()+1, self.calc_opt_size())
                    #self.entry_market_order('buy', Trade.get_bid_price()+1, self.calc_opt_size())
                elif predict[0] == 2:
                    self.entry_order('sell', TickData.get_ask_price() - 1, self.calc_opt_size())
                    #self.entry_order('sell', Trade.get_ask_price()-1, self.calc_opt_size())
                    #self.entry_market_order('sell', Trade.get_bid_price() + 1, self.calc_opt_size())
            elif self.posi_side == '' and self.order_side != '': #no position and ordering
                if (self.order_side == 'buy' and self.posi_side=='' and (predict[0] == 2)) or (self.order_side == 'sell' and self.posi_side =='' and (predict[0] == 1)):#ノーポジでオーダーが判定を逆の時にキャンセル。
                    self.cancel_order()
            elif self.posi_side != '' and self.order_side == '': #holding position and no order
                self.pl_order()
            #elif self.posi_side == 'buy' and (predict[0] == 2 or predict[0] == 3) or self.posi_side == 'sell' and (predict[0] == 1   or predict[0] == 3): # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。。
            elif (self.posi_side == 'buy' and predict[0] == 2) or (self.posi_side == 'sell' and predict[0] == 1):  # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。。
                self.exit_order()
                if self.order_status == 'pl ordering':
                    self.cancel_order()
            elif self.posi_side != '':
                self.calc_holding_pl()
            if self.order_side != '':
                self.check_execution()
            if Trade.flg_api_limit:
                time.sleep(60)
                print('Bot sleeping for 60sec due to API access limitation')
            else:
                time.sleep(1)


if __name__ == '__main__':
    SystemFlg.initialize()
    Trade.initialize()
    LogMaster.initialize()
    LineNotification.initialize()
    bot = Bot()
    bot.start_bot(500, 30, 100, 1)






