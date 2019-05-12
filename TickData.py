import threading
from WebsocketMaster import WebsocketMaster



class TickData:
    @classmethod
    def initialize(cls):
        cls.lock = threading.Lock()
        cls.ltp = 0
        cls.ws_execution = WebsocketMaster('lightning_executions_', 'FX_BTC_JPY')

    @classmthod
    def start_thread(self):
