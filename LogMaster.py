'''
dt, close, posi side, posi price, posi size, order side, order price, order size, # private access, # public access, # private access per min,
 pl, num trade, win rate, prediction, API errors, action message,
'''


class LogMaster:
    @classmethod
    def initialize(cls):
        cls.index = []
        cls.dt_log = {}
        cls.close = {}
        cls.posi_side = {}
        cls.posi_price = {}
        cls.posi_size = {}
        cls.order_side = {}
        cls.order_price = {}
        cls.order_size = {}
        cls.num_private_access = {}
        cls.num_public_access = {}
        cls.num_private_per_min = {}
        cls.num_trade = {}
        cls.win_rate = {}
        cls.prediction = {}
        cls.api_error = {}
        cls.action_message = {}

    @classmethod
    def add_log(cls,):








