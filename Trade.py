import ccxt
import time
import copy


class Trade:
    @classmethod
    def initialize(cls):
        cls.secret_key = ''
        cls.api_key = ''
        cls.__read_keys()
        cls.bf = ccxt.bitflyer({
            'apiKey': cls.api_key,
            'secret': cls.secret_key,
        })
        # print(cls.bf.fetch_trades(symbol='BTC/JPY', limit=2))
        # print(cls.bf.fetch_balance())
        # print(cls.bf.has)
        cls.order_id = {}
        cls.num_private_access = 0
        cls.num_public_access = 0

    @classmethod
    def __read_keys(cls):
        file = open('./ignore/ex.txt', 'r')  # 読み込みモードでオープン
        cls.secret_key = file.readline().split(':')[1]
        cls.secret_key = cls.secret_key[:len(cls.secret_key) - 1]
        cls.api_key = file.readline().split(':')[1]
        cls.api_key = cls.api_key[:len(cls.api_key) - 1]
        file.close()

    @classmethod
    def order(cls, side, price, size, expire_m) -> str:  # min size is 0.01
        cls.num_private_access += 1
        order_id = cls.bf.create_order(
            symbol='BTC/JPY',
            type='limit',
            side=side,
            price=price,
            amount=size,
            # params={'product_code': 'FX_BTC_JPY'}
            params={'product_code': 'FX_BTC_JPY', 'minute_to_expire': expire_m}  # 期限切れまでの時間（分）（省略した場合は30日）
        )['info']['child_order_acceptance_id']
        print('ok order - ' + str(order_id))
        return order_id

    '''
        {'id': 0, 'child_order_id': 'JFX20190218-133228-026751F', 'product_code': 'FX_BTC_JPY', 'side': 'BUY', 'child_order_type': 'LIMIT', 'price': 300000.0, 'average_price': 0.0, 'size': 0.01, 'child_order_state': 'ACTIVE', 'expire_date': '2019-03-20T13:32:16', 'child_order_date': '2019-02-18T13:32:16', 'child_order_acceptance_id': 'JRF20190218-133216-339861', 'outstanding_size': 0.01, 'cancel_size': 0.0, 'executed_size': 0.0, 'total_commission': 0.0}
    {'id': 729015336, 'child_order_id': 'JFX20181130-101920-984655F', 'product_code': 'FX_BTC_JPY', 'side': 'SELL', 'child_order_type': 'MARKET', 'price': 0.0, 'average_price': 459261.0, 'size': 0.2, 'child_order_state': 'COMPLETED', 'expire_date': '2019-11-30T10:19:20.167', 'child_order_date': '2018-11-30T10:19:20.167', 'child_order_acceptance_id': 'JUL20181130-101920-024232', 'outstanding_size': 0.0, 'cancel_size': 0.0, 'executed_size': 0.2, 'total_commission': 0.0}
    {'id': 727994097, 'child_order_id': 'JFX20181130-035459-398879F', 'product_code': 'FX_BTC_JPY', 'side': 'BUY', 'child_order_type': 'LIMIT', 'price': 484534.0, 'average_price': 484351.0, 'size': 0.2, 'child_order_state': 'COMPLETED', 'expire_date': '2018-12-30T03:54:59', 'child_order_date': '2018-11-30T03:54:59', 'child_order_acceptance_id': 'JRF20181130-035459-218762', 'outstanding_size': 0.0, 'cancel_size': 0.0, 'executed_size': 0.2, 'total_commission': 0.0}
    *expired / cancelled order are not shown in the order status, return []
    '''

    @classmethod
    def get_order_status(cls, id) -> []:
        cls.num_private_access += 1
        res = []
        try:
            res = cls.bf.private_get_getchildorders(
                params={'product_code': 'FX_BTC_JPY', 'child_order_acceptance_id': id})
        except Exception as e:
            print('error in get_order_status ' + e)
        finally:
            return res

    '''
    [{'id': 'JRF20190220-140338-069226',
    'info': {'id': 0,
    'child_order_id': 'JFX20190220-140338-309092F',
    'product_code': 'FX_BTC_JPY',
    'side': 'BUY',
    'child_order_type': 'LIMIT',
    'price': 300000.0,
    'average_price': 0.0,
    'size': 0.01,
    'child_order_state': 'ACTIVE',
    'expire_date': '2019-03-22T14:03:38',
    'child_order_date': '2019-02-20T14:03:38',
    'child_order_acceptance_id': 'JRF20190220-140338-069226',
    'outstanding_size': 0.01,
    'cancel_size': 0.0,
    'executed_size': 0.0,
    'total_commission': 0.0},
    'timestamp': 1550671418000,
    'datetime': '2019-02-20T14:03:38.000Z',
    'lastTradeTimestamp': None,
    'status': 'open',
    'symbol': 'BTC/JPY',
    'type': 'limit',
    'side': 'buy',
    'price': 300000.0,
    'cost': 0.0,
    'amount': 0.01,
    'filled': 0.0,
    'remaining': 0.01,
    'fee': {'cost': 0.0, 'currency': None, 'rate': None}},
    {'id': 'JRF20190220-140705-138578',
    'info': {'id': 0,
    'child_order_id': 'JFX20190220-140705-632784F',
    'product_code': 'FX_BTC_JPY',
    'side': 'BUY',
    'child_order_type': 'LIMIT',
    'price': 300001.0,
    'average_price': 0.0,
    'size': 0.01,
    'child_order_state': 'ACTIVE',
    'expire_date': '2019-03-22T14:07:05',
    'child_order_date': '2019-02-20T14:07:05',
    'child_order_acceptance_id': 'JRF20190220-140705-138578',
    'outstanding_size': 0.01,
    'cancel_size': 0.0,
    'executed_size': 0.0,
    'total_commission': 0.0},
    'timestamp': 1550671625000,
    'datetime': '2019-02-20T14:07:05.000Z',
    'lastTradeTimestamp': None,
    'status': 'open',
    'symbol': 'BTC/JPY',
    'type': 'limit',
    'side': 'buy',
    'price': 300001.0,
    'cost': 0.0,
    'amount': 0.01,
    'filled': 0.0,
    'remaining': 0.01,
    'fee': {'cost': 0.0, 'currency': None, 'rate': None}}]
    '''

    @classmethod
    def get_orders(cls):
        cls.num_private_access += 1
        orders = cls.bf.fetch_open_orders(symbol='BTC/JPY', params={"product_code": "FX_BTC_JPY"})
        return orders

    '''
    [{'id': 'JRF20190301-150253-171485',
  'info': {'id': 0,
   'child_order_id': 'JFX20190301-150253-315476F',
   'product_code': 'FX_BTC_JPY',
   'side': 'BUY',
   'child_order_type': 'LIMIT',
   'price': 300000.0,
   'average_price': 0.0,
   'size': 0.01,
   'child_order_state': 'ACTIVE',
   'expire_date': '2019-03-01T15:03:53',
   'child_order_date': '2019-03-01T15:02:53',
   'child_order_acceptance_id': 'JRF20190301-150253-171485',
   'outstanding_size': 0.01,
   'cancel_size': 0.0,
   'executed_size': 0.0,
   'total_commission': 0.0},
  'timestamp': 1551452573000,
  'datetime': '2019-03-01T15:02:53.000Z',
  'lastTradeTimestamp': None,
  'status': 'open',
  'symbol': 'BTC/JPY',
  'type': 'limit',
  'side': 'buy',
  'price': 300000.0,
  'cost': 0.0,
  'amount': 0.01,
  'filled': 0.0,
  'remaining': 0.01,
  'fee': {'cost': 0.0, 'currency': None, 'rate': None}}]
    '''

    @classmethod
    def get_order(cls, order_id):
        cls.num_private_access += 1
        order = cls.bf.fetch_open_orders(symbol='BTC/JPY',
                                         params={"product_code": "FX_BTC_JPY", 'child_order_acceptance_id': order_id})
        return order

    '''
    [{'product_code': 'FX_BTC_JPY',
    'side': 'BUY',
    'price': 434500.0,
    'size': 0.01,
    'commission': 0.0,
    'swap_point_accumulate': 0.0,
    'require_collateral': 289.6666666666667,
    'open_date': '2019-02-20T14:28:43.447',
    'leverage': 15.0,
    'pnl': -0.3,
    'sfd': 0.0}]
    '''

    @classmethod
    def get_positions(cls):  # None
        cls.num_private_access += 1
        positions = cls.bf.private_get_getpositions(params={"product_code": "FX_BTC_JPY"})
        return positions

    @classmethod
    def cancel_order(cls, order_id):
        cls.num_private_access += 1
        try:
            res = cls.bf.cancel_order(id=order_id, symbol='BTC/JPY', params={"product_code": "FX_BTC_JPY"})
        except Exception as e:
            print(e)

    @classmethod
    def get_current_asset(cls):
        cls.num_private_access += 1
        try:
            res = cls.bf.fetch_balance()
        except Exception as e:
            print('error i get_current_asset ' + e)
        finally:
            return res['total']['BTC'] * cls.get_opt_price() + res['total']['JPY']

    @classmethod
    def cancel_all_orders(cls):
        orders = cls.get_orders()
        for o in orders:
            cls.cancel_order(o['id'])

    @classmethod
    def price_tracing_order(cls, side, size) -> float:
        print('started price tracing order')
        remaining_size = size
        ave_exec_price = 0
        sum_price_x_size = 0
        while remaining_size > 0:
            price = cls.get_opt_price()
            order_id = cls.order_wait_till_boarding(side, price, remaining_size, 100)['child_order_acceptance_id']
            while abs(price - cls.get_opt_price()) <= 300:  # loop when current order price is close to opt price
                status = cls.get_order_status(order_id)
                if len(status) > 0:
                    remaining_size = status[0]['understanding_size']
                    print('executed @' + str(status[0]['average_price']) + ' x ' + str(status[0]['executed_size']))
                    if remaining_size == 0:
                        return ave_exec_price
                time.sleep(1)
            status = cls.cancel_and_wait_completion(order_id)  # when order price is far from opt price
            if len(status) > 0:
                remaining_size = status[0]['executed_size']
                print('executed @' + str(status[0]['average_price']) + ' x ' + str(status[0]['executed_size']))
        print('price tracing order has been completed')
        return ave_exec_price

    '''
    #res['bids'][0][0] = 394027
    {'bids': [[394027.0, 0.15], [394022.0, 0.01], [394020.0, 3.22357434], [394018.0, 0.02050665], [394016.0, 0.085], [394015.0, 0.02], [394014.0, 0.025], [394013.0, 0.21195378], [394012.0, 1.67], [394011.0, 1.36], [394010.0, 0.395], [394009.0, 0.01], [394008.0, 0.021], [394007.0, 0.09018275], [394006.0, 1.4862514], [394005.0, 6.42], [394004.0, 0.79593158], [394003.0, 5.0], [394002.0, 0.34592307], [394001.0, 4.14846844], [394000.0, 173.92494563], [393999.0, 0.01], [393998.0, 0.55], [393997.0, 0.484], [393996.0,
    '''

    @classmethod
    def get_order_book(cls):
        cls.num_private_access += 1
        return cls.bf.fetch_order_book(symbol='BTC/JPY', params={"product_code": "FX_BTC_JPY"})

    @classmethod
    def get_opt_price(cls):
        book = cls.get_order_book()
        bids = book['bids']
        asks = book['asks']
        bid = bids[0][0]
        ask = asks[0][0]
        return round(ask + float(ask - bid) / 2.0, 0)

    @classmethod
    def get_bid_price(cls):
        return cls.get_order_book()['bids'][0][0]

    @classmethod
    def get_ask_price(cls):
        return cls.get_order_book()['asks'][0][0]

    @classmethod
    def get_spread(cls):
        book = cls.get_order_book()
        return book['asks'][0][0] - book['bids'][0][0]

    '''
    ok orderJRF20190220-144017-685161
    waiting order execution...1 sec
    waiting order execution...2 sec
    [{'id': 967727288, 'child_order_id': 'JFX20190220-144017-948999F', 'product_code': 'FX_BTC_JPY', 'side': 'SELL', 'child_order_type': 'LIMIT', 'price': 434559.0, 'average_price': 434600.0, 'size': 0.01, 'child_order_state': 'COMPLETED', 'expire_date': '2019-03-22T14:40:17', 'child_order_date': '2019-02-20T14:40:17', 'child_order_acceptance_id': 'JRF20190220-144017-685161', 'outstanding_size': 0.0, 'cancel_size': 0.0, 'executed_size': 0.01, 'total_commission': 0.0}]
    order executed
    '''

    @classmethod
    def order_wait_till_execution(cls, side, price, size, expire_m) -> dict:
        id = cls.order(side, price, size, expire_m)
        i = 0
        print('waiting order execution...')
        flg_activated = False
        while True:
            status = cls.get_order_status(id)
            if len(status) > 0:
                if status[0]['child_order_state'] == 'COMPLETED':  # order executed
                    print('order has been executed')
                    return status[0]
                elif status[0]['child_order_state'] == 'ACTIVE':
                    flg_activated = True
            else:
                if flg_activated:
                    print('order has been expired')
                    return None
                i += 1
            time.sleep(10)

    @classmethod
    def cancel_and_wait_completion(cls, oid) -> dict:
        cls.cancel_order(oid)
        print('waiting cancell order ' + oid)
        time.sleep(2)
        while True:  # loop for check cancel completion or execution
            flg = True
            status = cls.get_order_status(oid)
            if len(status) > 0:
                if status[0]['child_order_state'] == 'COMPLETED':
                    print('cancel failed order has been executed')
                    return status[0]
            else:
                print('order has been successfully cancelled')
                return []
            time.sleep(1)

    @classmethod
    def order_wait_till_boarding(cls, side, price, size, expire_m) -> dict:
        oid = cls.order(side, price, size, expire_m)
        while True:
            status = cls.get_order_status(oid)
            if len(status) > 0:
                if status[0]['child_order_state'] == 'ACTIVE' or status[0]['child_order_state'] == 'COMPLETED':
                    print('confirmed the order has been boarded')
                    return status[0]
            time.sleep(1)



if __name__ == '__main__':
    Trade.initialize()
    oid = Trade.order('buy', 500000, 0.1, 1)
    print(Trade.get_order_status(oid))
    time.sleep(3)
    print(Trade.get_order_status(oid)[0])
    Trade.cancel_order(oid)
    time.sleep(5)
    print(Trade.get_order_status(oid)[0])





