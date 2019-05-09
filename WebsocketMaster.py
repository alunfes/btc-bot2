import websocket
import threading
import time
import json
import asyncio
from SystemFlg import SystemFlg
from numba import jit

class WebsocketMaster:
    def __init__(self, channel, symbol=''):
        self.symbol = symbol
        self.ticker = None
        self.message = None
        self.exection = None
        self.channel = channel
        self.connect()
        self.time_start = time.time()

    def connect(self):
        self.ws = websocket.WebSocketApp(
            'wss://ws.lightstream.bitflyer.com/json-rpc', header=None,
            on_open = self.on_open, on_message = self.on_message,
            on_error = self.on_error, on_close = self.on_close)
        self.ws.keep_running = True
        websocket.enableTrace(True)
        self.thread = threading.Thread(target=lambda: self.ws.run_forever())
        #self.thread.daemon = True
        self.thread.start()

    @jit
    def is_connected(self):
        return self.ws.sock and self.ws.sock.connected

    @jit
    def disconnect(self):
        print('disconnected')
        self.ws.keep_running = False
        self.ws.close()

    @jit
    def get(self):
        return self.ticker

    @jit
    def get_ltp(self):
        if self.ticker is not None:
            return self.ticker['ltp']
        else:
            return None

    @jit
    def get_best_bid(self): #for buy
        if self.ticker is not None:
            return self.ticker['best_bid']
        else:
            return None

    @jit
    def get_best_ask(self): #for sell
        if self.ticker is not None:
            return self.ticker['best_ask']
        else:
            return None

    @jit
    def get_buy_child_order_acceptance_id(self):
        if self.exection is not None:
            return self.exection[-1]['buy_child_order_acceptance_id']
        else:
            return None

    '''
    lightning_executions_
    [{'id': 1046951795, 'side': 'SELL', 'price': 654622, 'size': 0.1, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-516068', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951796, 'side': 'SELL', 'price': 654614, 'size': 0.034, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-279674', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951797, 'side': 'SELL', 'price': 654613, 'size': 0.01, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-172141', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951798, 'side': 'SELL', 'price': 654613, 'size': 0.01, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-785127', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951799, 'side': 'SELL', 'price': 654613, 'size': 0.02, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-007355', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951800, 'side': 'SELL', 'price': 654612, 'size': 0.01, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-172142', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951801, 'side': 'SELL', 'price': 654611, 'size': 0.05, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-402171', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951802, 'side': 'SELL', 'price': 654609, 'size': 0.02, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-279677', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951803, 'side': 'SELL', 'price': 654604, 'size': 0.13673, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120320-007353', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951804, 'side': 'SELL', 'price': 654603, 'size': 0.02, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-353741', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951805, 'side': 'SELL', 'price': 654602, 'size': 0.6, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-167508', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951806, 'side': 'SELL', 'price': 654600, 'size': 0.2, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120322-681289', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951807, 'side': 'SELL', 'price': 654597, 'size': 0.2, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-066965', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951808, 'side': 'SELL', 'price': 654596, 'size': 0.08, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-279681', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951809, 'side': 'SELL', 'price': 654595, 'size': 0.08, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-516060', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951810, 'side': 'SELL', 'price': 654593, 'size': 0.01, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-402169', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}]
    [{'id': 1046951811, 'side': 'SELL', 'price': 654593, 'size': 0.17615827, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120322-007388', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951812, 'side': 'SELL', 'price': 654589, 'size': 0.01, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-282936', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951813, 'side': 'SELL', 'price': 654584, 'size': 0.05, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-279680', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951814, 'side': 'SELL', 'price': 654584, 'size': 0.2, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-066973', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951815, 'side': 'SELL', 'price': 654583, 'size': 0.01, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-516069', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951816, 'side': 'SELL', 'price': 654582, 'size': 0.01, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120310-785048', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951817, 'side': 'SELL', 'price': 654576, 'size': 0.01, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120314-402105', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951818, 'side': 'SELL', 'price': 654574, 'size': 0.06791747, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120310-279589', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951819, 'side': 'SELL', 'price': 654574, 'size': 0.01, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120318-007328', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951820, 'side': 'SELL', 'price': 654573, 'size': 0.2, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120315-007284', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951821, 'side': 'SELL', 'price': 654571, 'size': 0.05, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120310-007231', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951822, 'side': 'SELL', 'price': 654570, 'size': 0.2, 'exec_date': '2019-05-07T12:03:23.1848477Z', 'buy_child_order_acceptance_id': 'JRF20190507-120310-390157', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951823, 'side': 'SELL', 'price': 654565, 'size': 0.03181892, 'exec_date': '2019-05-07T12:03:23.2004712Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-007373', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681291'}, {'id': 1046951824, 'side': 'SELL', 'price': 654565, 'size': 0.04818108, 'exec_date': '2019-05-07T12:03:23.2004712Z', 'buy_child_order_acceptance_id': 'JRF20190507-120321-007373', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681293'}, {'id': 1046951825, 'side': 'SELL', 'price': 654560, 'size': 0.45181892, 'exec_date': '2019-05-07T12:03:23.2004712Z', 'buy_child_order_acceptance_id': 'JRF20190507-120322-167519', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681293'}]
    [{'id': 1046951826, 'side': 'SELL', 'price': 654560.0, 'size': 0.02, 'exec_date': '2019-05-07T12:03:23.3275613Z', 'buy_child_order_acceptance_id': 'JRF20190507-120322-167519', 'sell_child_order_acceptance_id': 'JRF20190507-120323-767279'}, {'id': 1046951827, 'side': 'SELL', 'price': 654604.0, 'size': 0.5, 'exec_date': '2019-05-07T12:03:23.4838055Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-033055', 'sell_child_order_acceptance_id': 'JRF20190507-120323-032026'}, {'id': 1046951828, 'side': 'SELL', 'price': 654604.0, 'size': 0.02, 'exec_date': '2019-05-07T12:03:23.5150556Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-033055', 'sell_child_order_acceptance_id': 'JRF20190507-120323-172154'}, {'id': 1046951829, 'side': 'BUY', 'price': 654631.0, 'size': 0.259, 'exec_date': '2019-05-07T12:03:23.7494228Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120323-007393'}, {'id': 1046951830, 'side': 'BUY', 'price': 654657.0, 'size': 0.05, 'exec_date': '2019-05-07T12:03:23.7494228Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120323-767280'}, {'id': 1046951831, 'side': 'BUY', 'price': 654729.0, 'size': 0.07615942, 'exec_date': '2019-05-07T12:03:23.7494228Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120323-516087'}, {'id': 1046951832, 'side': 'BUY', 'price': 654731.0, 'size': 0.07615942, 'exec_date': '2019-05-07T12:03:23.7494228Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120323-007394'}, {'id': 1046951833, 'side': 'BUY', 'price': 654742.0, 'size': 0.11, 'exec_date': '2019-05-07T12:03:23.7494228Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120323-066979'}, {'id': 1046951834, 'side': 'BUY', 'price': 654747.0, 'size': 0.091, 'exec_date': '2019-05-07T12:03:23.7494228Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120323-681294'}, {'id': 1046951835, 'side': 'BUY', 'price': 654750.0, 'size': 0.2, 'exec_date': '2019-05-07T12:03:23.7650461Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120323-167525'}, {'id': 1046951836, 'side': 'BUY', 'price': 654763.0, 'size': 2.77615942, 'exec_date': '2019-05-07T12:03:23.7650461Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120322-007379'}, {'id': 1046951837, 'side': 'BUY', 'price': 654764.0, 'size': 0.264, 'exec_date': '2019-05-07T12:03:23.7650461Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120323-066978'}, {'id': 1046951838, 'side': 'BUY', 'price': 654766.0, 'size': 0.06, 'exec_date': '2019-05-07T12:03:23.7650461Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120323-516088'}, {'id': 1046951839, 'side': 'BUY', 'price': 654769.0, 'size': 0.11725038, 'exec_date': '2019-05-07T12:03:23.7650461Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120322-353751'}, {'id': 1046951840, 'side': 'BUY', 'price': 654769.0, 'size': 0.2, 'exec_date': '2019-05-07T12:03:23.7650461Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120322-646397'}, {'id': 1046951841, 'side': 'BUY', 'price': 654776.0, 'size': 3.72027136, 'exec_date': '2019-05-07T12:03:23.7650461Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681296', 'sell_child_order_acceptance_id': 'JRF20190507-120322-402189'}]
    [{'id': 1046951842, 'side': 'BUY', 'price': 654643.0, 'size': 0.1, 'exec_date': '2019-05-07T12:03:23.9077646Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-033069', 'sell_child_order_acceptance_id': 'JRF20190507-120323-402203'}, {'id': 1046951843, 'side': 'BUY', 'price': 654643.0, 'size': 0.1, 'exec_date': '2019-05-07T12:03:23.9077646Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-390231', 'sell_child_order_acceptance_id': 'JRF20190507-120323-402203'}, {'id': 1046951844, 'side': 'BUY', 'price': 654643.0, 'size': 0.03, 'exec_date': '2019-05-07T12:03:24.0952599Z', 'buy_child_order_acceptance_id': 'JRF20190507-120323-681297', 'sell_child_order_acceptance_id': 'JRF20190507-120323-402203'}, {'id': 1046951845, 'side': 'BUY', 'price': 654643.0, 'size': 0.1, 'exec_date': '2019-05-07T12:03:24.2536212Z', 'buy_child_order_acceptance_id': 'JRF20190507-120324-681298', 'sell_child_order_acceptance_id': 'JRF20190507-120323-402203'}, {'id': 1046951846, 'side': 'BUY', 'price': 654643.0, 'size': 0.17, 'exec_date': '2019-05-07T12:03:24.2848715Z', 'buy_child_order_acceptance_id': 'JRF20190507-120324-066980', 'sell_child_order_acceptance_id': 'JRF20190507-120323-402203'}, {'id': 1046951847, 'side': 'BUY', 'price': 654687.0, 'size': 0.13, 'exec_date': '2019-05-07T12:03:24.2848715Z', 'buy_child_order_acceptance_id': 'JRF20190507-120324-066980', 'sell_child_order_acceptance_id': 'JRF20190507-120324-167526'}]
    '''
    '''
    lightning_ticker_
    {'product_code': 'FX_BTC_JPY', 'timestamp': '2019-05-07T12:25:52.2457622Z', 'tick_id': 45113277, 'best_bid': 654499.0, 'best_ask': 654544.0, 'best_bid_size': 0.786, 'best_ask_size': 0.0339062, 'total_bid_depth': 7917.99116313, 'total_ask_depth': 7520.12259162, 'ltp': 654544.0, 'volume': 484127.17608082, 'volume_by_product': 484127.17608082}
    {'product_code': 'FX_BTC_JPY', 'timestamp': '2019-05-07T12:25:52.8142083Z', 'tick_id': 45113364, 'best_bid': 654502.0, 'best_ask': 654622.0, 'best_bid_size': 0.09, 'best_ask_size': 0.24730589, 'total_bid_depth': 7913.28127613, 'total_ask_depth': 7504.00780466, 'ltp': 654634.0, 'volume': 484136.69094562, 'volume_by_product': 484136.69094562}
    {'product_code': 'FX_BTC_JPY', 'timestamp': '2019-05-07T12:25:54.3482242Z', 'tick_id': 45113515, 'best_bid': 654588.0, 'best_ask': 654622.0, 'best_bid_size': 0.00995455, 'best_ask_size': 0.17958601, 'total_bid_depth': 7912.32113241, 'total_ask_depth': 7516.2925372, 'ltp': 654622.0, 'volume': 484133.15209096, 'volume_by_product': 484133.15209096}
    '''

    @jit
    def on_message(self, ws, message):
        message = json.loads(message)['params']
        self.message = message['message']
        if self.channel == 'lightning_executions_':
            if self.message is not None:
                self.exection = self.message
                pass
        elif self.channel == 'lightning_ticker_':
            if self.message is not None:
                self.ticker = self.message
                pass
        if SystemFlg.get_system_flg() == False:
            self.disconnect()

    @jit
    def on_error(self, ws, error):
        print('error')
        self.disconnect()
        time.sleep(3)
        self.connect()

    @jit
    def on_close(self, ws):
        print('Websocket disconnected')

    @jit
    def on_open(self, ws):
        ws.send(json.dumps( {'method':'subscribe',
            'params':{'channel':self.channel + self.symbol}} ))
        time.sleep(1)
        print('Websocket connected')

    @jit
    async def loop(self):
        while True:
            await asyncio.sleep(1)


if __name__ == '__main__':
    SystemFlg.initialize()
    #ws_execution = WebsocketMaster('lightning_executions_', 'FX_BTC_JPY')
    ws_ticker = WebsocketMaster('lightning_ticker_', 'FX_BTC_JPY')
    time.sleep(5)
    while True:
        #print('current price='+str(ws_execution.get_current_price()))
        #print('bid='+str(ws_ticker.get_best_bid()))
        if ws_ticker.ticker is not None:
            print(ws_ticker.get_ltp())
        time.sleep(0.5)
    #num_failed = 0
    #loop = asyncio.get_event_loop()
    #asyncio.ensure_future(md.loop())
    #loop.run_forever()
    #md.disconnect()