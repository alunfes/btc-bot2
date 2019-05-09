import time
import asyncio
from SystemFlg import SystemFlg
from WebsocketMaster import WebsocketMaster
from MarketData2 import MarketData2
from Bot import  Bot
from LineNotification import LineNotification
from Trade import Trade
from LogMaster import LogMaster
import atexit
from numba import jit

class MasterThread:
    def __init__(self):
        SystemFlg.initialize()
        self.num_conti_fooker = 0

    @jit
    def __bot_fooker(self):
        self.num_conti_fooker += 1
        if SystemFlg.get_system_flg():
            if self.num_conti_fooker < 15:
                print('unexpected error was occured! restarted bot script.')
                self.start_master_thread()
            else:
                print('bot restarted more than 15times!')
                SystemFlg.set_system_flg(False)
                return 0
        else:
            print('bot has been correctely finished.')
            return 0

    @jit
    def start_master_thread(self):
        SystemFlg.initialize()
        Trade.initialize()
        LogMaster.initialize()
        LineNotification.initialize()
        bot = Bot()
        atexit.register(self.__bot_fooker)
        time.sleep(3)
        bot.start_bot(1600, 215, 100, 1)

    @jit
    def test_ws(self):
        ws_ticker = WebsocketMaster('lightning_ticker_', 'FX_BTC_JPY')
        ws_execution = WebsocketMaster('lightning_executions_', 'FX_BTC_JPY')
        while True:
            print('id='+str(ws_execution.get_buy_child_order_acceptance_id()))
            print('bid=' + str(ws_ticker.get_best_bid()))
            time.sleep(1)




if __name__ == '__main__':
    mt = MasterThread()
    mt.test_ws()
#    mt.start_master_thread()
