import ccxt
import time
import threading
from SystemFlg import SystemFlg
from LogMaster import LogMaster
from datetime import datetime
from LineNotification import LineNotification
from ProxyList import ProxyList

'''
Private API の呼出は 5 分間で 500 回を上限とします。上限に達すると呼出を一定時間ブロックします。また、ブロックの解除後も呼出の上限を一定時間引き下げます。
同一 IP アドレスからの API の呼出は 5 分間で 500 回を上限とします。上限に達すると呼出を一定時間ブロックします。また、ブロックの解除後も呼出の上限を一定時間引き下げます。
https://web.archive.org/web/20181001014248/https://fwww.me/2018/09/30/bitflyer-informal-api/
'''


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


        cls.bf_pub = ccxt.bitflyer()
        '''
        cls.bf_pub.proxies = {
            'http': 'http://10.10.10.10:3128',
            'https': 'http://10.10.10.10:3128',
        }
        cls.bf_pub.session.verify = False  # Do not reject on SSL certificate checks
        cls.bf_pub.session.trust_env = False  # Ignore any Environment HTTP/S Proxy and No_Proxy variables
        cls.bf_pub.load_markets()
        '''
        cls.order_id = {}
        cls.num_private_access = 0
        cls.num_public_access = 0
        cls.flg_api_limit = False
        cls.conti_order_error = 0
        cls.adjusting_sleep = 0
        cls.total_access_per_300s = 0
        th = threading.Thread(target=cls.monitor_api)
        th.start()
        #time.sleep(5)

    @classmethod
    def monitor_api(cls):
        i = 1
        pre_private_access = 0
        pre_public_access = 0
        cls.access_log = []
        cls.total_access_per_300s = 0
        while SystemFlg.get_system_flg():
            cls.access_log.append(cls.num_private_access + cls.num_public_access - pre_private_access - pre_public_access)
            pre_private_access =cls.num_private_access
            pre_public_access = cls.num_public_access
            if len(cls.access_log) >= 300:
                cls.total_access_per_300s = sum(cls.access_log[-300:])
                cls.access_log.pop(0)
                if cls.total_access_per_300s >= 5000000:
                    LineNotification.send_error('Total API access reached 500/sec! sleep for 60sec')
                    print('Total API access reached 500/sec! sleep for 60sec')
                    LogMaster.add_log({'dt': datetime.now(), 'api_error': 'Total API access reached 500/sec! sleep for 60sec'})
                    l = [0] * 60
                    cls.access_log.extend(l)
                    i += 60
                    cls.flg_api_limit = True
                    time.sleep(60)
                else:
                    cls.flg_api_limit = False
            time.sleep(1)
            i+=1

    @classmethod
    def check_exception(cls, exc):
        if 'Connection reset by peer' in str(exc):
            print('detected connection reset by peer error!')
            print('initialize trade class.')
            LineNotification.send_error('detected connection reset by peer error!')
            LogMaster.add_log({'dt': datetime.now(), 'api_error': 'detected connection reset by peer error!'})
            cls.initialize()
            time.sleep(10)
            return 'error'
        if 'Over API limit per minute' in str(exc):
            print('API private access reached limitation!')
            print('initialize trade class and sleep 60sec.')
            LineNotification.send_error('API private access reached limitation!')
            LogMaster.add_log({'dt': datetime.now(), 'api_error': 'API private access reached limitation!'})
            cls.flg_api_limit = True
            time.sleep(60)
            cls.initialize()
            return 'error'
        if 'Connection aborted.' in str(exc):
            print('Connection aborted error occurred!')
            print('initialize trade class and sleep 5sec.')
            LineNotification.send_error('Connection aborted.')
            LogMaster.add_log({'dt': datetime.now(), 'api_error': 'Connection aborted error occurred!'})
            cls.initialize()
            time.sleep(5)
            return 'error'
        return 'ok'



    @classmethod
    def __read_keys(cls):
        file = open('./ignore/ex.txt', 'r')  # 読み込みモードでオープン
        cls.secret_key = file.readline().split(':')[1]
        cls.secret_key = cls.secret_key[:len(cls.secret_key) - 1]
        cls.api_key = file.readline().split(':')[1]
        cls.api_key = cls.api_key[:len(cls.api_key) - 1]
        file.close()

    '''
    when margin is not sufficient - {"status":-205,"error_message":"Margin amount is insufficient for this order.","data":null}
    '''
    @classmethod
    def order(cls, side, price, size, type, expire_m) -> str:  # min size is 0.01
        if cls.flg_api_limit == False:
            order_id = ''
            if size >= 0.01:
                try:
                    if type == 'limit':
                        cls.num_private_access += 1
                        order_id = cls.bf.create_order(
                            symbol='BTC/JPY',
                            type='limit',
                            side=side,
                            price=price,
                            amount=size,
                            # params={'product_code': 'FX_BTC_JPY'}
                            params={'product_code': 'FX_BTC_JPY', 'minute_to_expire': expire_m}  # 期限切れまでの時間（分）（省略した場合は30日）
                        )
                    elif type == 'market':
                        cls.num_private_access += 1
                        order_id = cls.bf.create_order(
                            symbol='BTC/JPY',
                            type='market',
                            side=side,
                            amount=size,
                            # params={'product_code': 'FX_BTC_JPY'}
                            params={'product_code': 'FX_BTC_JPY'}
                        )
                    else:
                        print('Trade - order: invalid order type!')
                        LogMaster.add_log({'dt': datetime.now(),'api_error': 'Trade - order: invalid order type!'})
                        LineNotification.send_error('Trade - order: invalid order type!')
                        return ''
                except Exception as e:
                    if 'Margin amount is insufficient' in str(e):
                        size -= 0.01
                        size = round(size,2)
                        print('margin amount is insufficient! - decrease order size to '+str(size))
                        return cls.order(side,price,size, type, expire_m)
                    elif 'Market state is closed.' in str(e):
                        print(str(datetime.now())+': market state is closed.')
                        time.sleep(10)
                        return cls.order(side, price, size, type, expire_m)
                    else:
                        print(e)
                        LogMaster.add_log({'dt': datetime.now(), 'action_message': 'Trade-order error! ' + str(e)})
                        cls.conti_order_error += 1
                        if cls.check_exception(e) == 'ok':
                            if cls.conti_order_error > 15:
                                SystemFlg.set_system_flg(False)
                                LogMaster.add_log({'dt':datetime.now(),'api_error':'continuous order error more than 15times System Finished.'})
                                print('continuous order error more than 15times System Finished.')
                            return ''
                        else: #connection reset by peer error
                            return ''
                order_id = order_id['info']['child_order_acceptance_id']
                cls.conti_order_error = 0
                print('ok order - ' + str(order_id))
                return order_id
            else:
                print('order size ' + str(size) + ' is too small. minimum order size is 0.01!')
                l = len(str(size)) - 2
                print('first order size='+str(round(size+0.01,l)))
                cls.price_tracing_order(side, round(size+0.01,l))
                print('second order')
                cls.price_tracing_order('buy' if side =='sell' else 'sell',0.01)
        else:
            print('order is temporary exhibited due to API access limitation!')
            return ''


    '''
        {'id': 0, 'child_order_id': 'JFX20190218-133228-026751F', 'product_code': 'FX_BTC_JPY', 'side': 'BUY', 'child_order_type': 'LIMIT', 'price': 300000.0, 'average_price': 0.0, 'size': 0.01, 'child_order_state': 'ACTIVE', 'expire_date': '2019-03-20T13:32:16', 'child_order_date': '2019-02-18T13:32:16', 'child_order_acceptance_id': 'JRF20190218-133216-339861', 'outstanding_size': 0.01, 'cancel_size': 0.0, 'executed_size': 0.0, 'total_commission': 0.0}
    {'id': 729015336, 'child_order_id': 'JFX20181130-101920-984655F', 'product_code': 'FX_BTC_JPY', 'side': 'SELL', 'child_order_type': 'MARKET', 'price': 0.0, 'average_price': 459261.0, 'size': 0.2, 'child_order_state': 'COMPLETED', 'expire_date': '2019-11-30T10:19:20.167', 'child_order_date': '2018-11-30T10:19:20.167', 'child_order_acceptance_id': 'JUL20181130-101920-024232', 'outstanding_size': 0.0, 'cancel_size': 0.0, 'executed_size': 0.2, 'total_commission': 0.0}
    {'id': 727994097, 'child_order_id': 'JFX20181130-035459-398879F', 'product_code': 'FX_BTC_JPY', 'side': 'BUY', 'child_order_type': 'LIMIT', 'price': 484534.0, 'average_price': 484351.0, 'size': 0.2, 'child_order_state': 'COMPLETED', 'expire_date': '2018-12-30T03:54:59', 'child_order_date': '2018-11-30T03:54:59', 'child_order_acceptance_id': 'JRF20181130-035459-218762', 'outstanding_size': 0.0, 'cancel_size': 0.0, 'executed_size': 0.2, 'total_commission': 0.0}
    [{'id': 1151189020, 'child_order_id': 'JFX20190422-121505-060051F', 'product_code': 'FX_BTC_JPY', 'side': 'BUY', 'child_order_type': 'LIMIT', 'price': 601306.0, 'average_price': 601306.0, 'size': 0.06, 'child_order_state': 'CANCELED', 'expire_date': '2019-04-22T13:55:05', 'child_order_date': '2019-04-22T12:15:05', 'child_order_acceptance_id': 'JRF20190422-121505-247049', 'outstanding_size': 0.0, 'cancel_size': 0.02, 'executed_size': 0.04, 'total_commission': 0.0}]
    *expired / cancelled order are not shown in the order status, return []
    '''

    @classmethod
    def get_order_status(cls, id) -> []:
        if cls.flg_api_limit == False:
            res = []
            try:
                cls.num_private_access += 1
                res = cls.bf.private_get_getchildorders(
                    params={'product_code': 'FX_BTC_JPY', 'child_order_acceptance_id': id})
            except Exception as e:
                if cls.check_exception(e) == 'ok':
                    pass
                print('error in get_order_status ' + str(e))
                LogMaster.add_log({'dt': datetime.now(),'api_error': 'Trade-get order status error! '+str(e)})
                LineNotification.send_error('api_error:Trade-get order status error!'+str(e))
            finally:
                return res
        else:
            print('get_order_status is temporary exhibited due to API access limitation!')
            return None

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
        try:
            cls.num_private_access += 1
            orders = cls.bf.fetch_open_orders(symbol='BTC/JPY', params={"product_code": "FX_BTC_JPY"})
        except Exception as e:
            print('error in get_orders ' + str(e))
            LogMaster.add_log({'dt': datetime.now(), 'api_error': 'Trade-get get_orders error! ' + str(e)})
            cls.check_exception(e)
            time.sleep(3)
            return cls.get_orders()
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
        try:
            cls.num_private_access += 1
            order = cls.bf.fetch_open_orders(symbol='BTC/JPY', params={"product_code": "FX_BTC_JPY", 'child_order_acceptance_id': order_id})
        except Exception as e:
            print('error in get_order ' + str(e))
            LogMaster.add_log({'dt': datetime.now(), 'api_error': 'Trade-get get_order error! ' + str(e)})
            if cls.check_exception(e) == 'ok':
                pass
            else:
                return cls.get_order(order_id)
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
        try:
            cls.num_private_access += 1
            positions = cls.bf.private_get_getpositions(params={"product_code": "FX_BTC_JPY"})
        except Exception as e:
            print('error in get_positions ' + str(e))
            LogMaster.add_log({'dt': datetime.now(), 'api_error': 'Trade-get get_positions error! ' + str(e)})
            if cls.check_exception(e) == 'ok':
                pass
            else:
                return cls.get_positions()
        return positions

    @classmethod
    def cancel_order(cls, order_id):
        cancel =''
        try:
            cls.num_private_access += 1
            cancel = cls.bf.cancel_order(id=order_id, symbol='BTC/JPY', params={"product_code": "FX_BTC_JPY"})
        except Exception as e:
            print('error in cancel_order ' + str(e))
            LogMaster.add_log({'dt': datetime.now(), 'api_error': 'Trade-get cancel_order error! ' + str(e)})
            cls.check_exception(e)
            if 'Order not found' in str(e):
                print('cancel order not found!')
                LogMaster.add_log({'dt': datetime.now(), 'api_error': 'cancel order not found! '})
                cancel = ''
        return cancel

    @classmethod
    def get_current_asset(cls):
        try:
            cls.num_private_access += 1
            res = cls.bf.fetch_balance()
        except Exception as e:
            print('error i get_current_asset ' + e)
            LogMaster.add_log({'dt': datetime.now(), 'action_message': 'Trade-get current asset error! ' + str(e)})
            if cls.check_exception(e) == 'ok':
                pass
        finally:
            return res['total']['BTC'] * cls.get_opt_price() + res['total']['JPY']


    #{'collateral': 5094.0, 'open_position_pnl': 0.0, 'require_collateral': 0.0, 'keep_rate': 0.0}
    @classmethod
    def get_collateral(cls):
        res=''
        try:
            cls.num_private_access += 1
            res = cls.bf.fetch2(path='getcollateral', api='private', method='GET')
        except Exception as e:
            print('error i get_collateral ' + e)
            LogMaster.add_log({'dt': datetime.now(), 'api_error': 'Trade-get get_collateral error! ' + str(e)})
            if cls.check_exception(e) == 'ok':
                pass
        finally:
            return res

    @classmethod
    def cancel_all_orders(cls):
        orders = cls.get_orders()
        for o in orders:
            cls.cancel_order(o['id'])

    '''
    can't handle if existing positions
    assumed only when exit from current position
    '''
    @classmethod
    def price_tracing_order(cls, side, size) -> float:
        if cls.flg_api_limit == False:
            print('started price tracing order')
            remaining_size = size
            sum_price_x_size = 0
            sum_size = 0
            pre_exe_size = 0
            price = cls.get_opt_price()
            #price = cls.get_opt_buy_price() if side == 'buy' else cls.get_opt_sell_price()
            order_id = cls.order_wait_till_boarding(side, price, remaining_size, 100)['child_order_acceptance_id']
            num_loop = 0
            while remaining_size > 0:
                status = cls.get_order_status(order_id)
                if abs(price - cls.get_opt_price()) >= 100 and remaining_size > 0:  # current order price is far from opt price
                #if abs(price - cls.get_opt_buy_price() if side == 'buy' else cls.get_opt_sell_price()) >= 30 and remaining_size > 0:  # current order price is far from opt price
                    res = cls.cancel_and_wait_completion(order_id)
                    if len(res) > 0:  # cancell failed order partially executed
                        remaining_size = res['outstanding_size']
                        sum_price_x_size += float(res['average_price']) * float(res['executed_size'] - pre_exe_size)
                        sum_size += float(res['executed_size'] - pre_exe_size)
                        print('price tracing order - executed ' + str(res['executed_size'] - pre_exe_size) + ' @' + str(res['average_price']))
                        if remaining_size <= 0:  # target size has been executed
                            break
                        else:  # place a new order for remaining size
                            pre_exe_size = status[0]['executed_size']
                            price = cls.get_opt_price()
                            order_id = cls.order_wait_till_boarding(side, price, remaining_size, 100)['child_order_acceptance_id']
                            print('price tracing order - placed new order for remaining size. size = '+str(remaining_size))
                            #print('price tracing order - executed ' + str(res['executed_size'] - pre_exe_size) + ' @' + str(res['average_price']))
                    else:
                        price = cls.get_opt_price()
                        #price = cls.get_opt_buy_price() if side == 'buy' else cls.get_opt_sell_price()
                        order_id = cls.order_wait_till_boarding(side, price, remaining_size, 100)['child_order_acceptance_id']
                        print('price tracing order - replaced order for ' + side + ', @' + str(price) + ' x ' + str(remaining_size))
                        pre_exe_size = 0
                if len(status) > 0:
                    if status[0]['outstanding_size'] == 0:  # excuted all portion
                        sum_price_x_size += float(status[0]['average_price']) * float(status[0]['executed_size'] - pre_exe_size)
                        sum_size += float(status[0]['executed_size'] - pre_exe_size)
                        remaining_size = 0
                        pre_exe_size = 0
                        break
                    else:
                        if status[0]['outstanding_size'] < remaining_size:
                            sum_price_x_size += float(status[0]['average_price']) * float(status[0]['executed_size'] - pre_exe_size)
                            sum_size += float(status[0]['executed_size'] - pre_exe_size)
                            remaining_size = status[0]['outstanding_size']
                            print('price tracing order - executed ' + str(status[0]['executed_size'] - pre_exe_size) + ' @' + str(price))
                            pre_exe_size = status[0]['executed_size']
                time.sleep(0.5)
                num_loop += 1
                if num_loop > 100:
                    print('price tracing order loop too many!')
                    print(status)
                    print(remaining_size)
                    print(order_id)
                    print(pre_exe_size)
                    if sum_size > 0:
                        print('ave price={}, exe size = {}'.format(sum_price_x_size / sum_size, sum_size))
                        return sum_price_x_size / sum_size
                    else:
                        print('ave price={}, exe size = {}'.format(0, 0))
                        return ''
            Trade.cancel_all_orders()
            print('price tracing order has been completed.')
            print('ave price={}, exe size = {}'.format(sum_price_x_size / sum_size, sum_size))
            return sum_price_x_size / sum_size
        else:
            print('order is temporary exhibited due to API access limitation!')
            return ''

    '''
    #res['bids'][0][0] = 394027
    {'bids': [[394027.0, 0.15], [394022.0, 0.01], [394020.0, 3.22357434], [394018.0, 0.02050665], [394016.0, 0.085], [394015.0, 0.02], [394014.0, 0.025], [394013.0, 0.21195378], [394012.0, 1.67], [394011.0, 1.36], [394010.0, 0.395], [394009.0, 0.01], [394008.0, 0.021], [394007.0, 0.09018275], [394006.0, 1.4862514], [394005.0, 6.42], [394004.0, 0.79593158], [394003.0, 5.0], [394002.0, 0.34592307], [394001.0, 4.14846844], [394000.0, 173.92494563], [393999.0, 0.01], [393998.0, 0.55], [393997.0, 0.484], [393996.0,
    '''
    @classmethod
    def get_order_book(cls):
        cls.num_public_access += 1
        return cls.bf_pub.fetch_order_book(symbol='BTC/JPY', params={"product_code": "FX_BTC_JPY"})

    @classmethod
    def get_last_price(cls):
        try:
            cls.num_public_access += 1
            ticker = cls.bf_pub.fetch_ticker('BTC/JPY', params={"product_code": "FX_BTC_JPY"})
        except Exception as e:
            print('error i get_last_price ' + str(e))
            LogMaster.add_log({'dt': datetime.now(), 'api_error': 'Trade-get get_last_price error! ' + str(e)})
            cls.check_exception(e)
            return cls.get_last_price()
        return ticker['last']

    @classmethod
    def get_current_price(cls):
        return cls.ws_ticker.get_current_price()

    @classmethod
    def get_opt_price(cls):
        book = cls.get_order_book()
        bids = book['bids']
        asks = book['asks']
        bid = bids[0][0]
        ask = asks[0][0]
        return round(ask + float(ask - bid) / 2.0, 0)

    @classmethod
    def get_opt_buy_price(cls):
        return cls.ws_ticker.get_opt_buy_price

    @classmethod
    def get_opt_sell_price(cls):
        return cls.ws_ticker.get_opt_sell_price

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
        id = cls.order(side, price, size, 'limit', expire_m)
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
            time.sleep(1)

    '''
    new entryしたオーダーが1秒後にもまだboardしておらず、cancel and wait orderでorder status取得できず、誤ってsuccessfully cancelledと判定されうるので、
    最初にorder statusが存在することを確認している。
    5秒経ってもorder statusが確認できない時はcancelledとして処理する。
    '''
    @classmethod
    def cancel_and_wait_completion(cls, oid) -> dict:
        status = cls.get_order_status(oid)
        if len(status) == 0:
            n = 0
            while len(status) == 0:
                time.sleep(1)
                n += 1
                status = cls.get_order_status(oid)
                if n > 5:
                    print('cancel_and_wait_completion -  order status is not available!')
                    return []
        cls.cancel_order(oid)
        print('waiting cancel order ' + oid)
        time.sleep(1)
        while True:  # loop for check cancel completion or execution
            status = cls.get_order_status(oid)
            if len(status) > 0:
                if (status[0]['child_order_state'] == 'COMPLETED' or status[0]['child_order_state'] == 'CANCELED') and status[0]['executed_size'] > 0:
                    print('cancel failed order has been partially executed. exe size='+str(status[0]['executed_size']))
                    return status[0]
                elif (status[0]['child_order_state'] == 'COMPLETED' or status[0]['child_order_state'] == 'CANCELED') and status[0]['executed_size'] == 0:
                    print('order has been successfully cancelled')
                    return []
            else:
                print('order has been successfully cancelled')
                return []
            time.sleep(0.5)

    @classmethod
    def order_wait_till_boarding(cls, side, price, size, expire_m) -> dict:
        oid = cls.order(side, price, size, 'limit', expire_m)
        while True:
            status = cls.get_order_status(oid)
            if len(status) > 0:
                if status[0]['child_order_state'] == 'ACTIVE' or status[0]['child_order_state'] == 'COMPLETED':
                    print('confirmed the order has been boarded')
                    return status[0]
            time.sleep(0.5)



if __name__ == '__main__':
    SystemFlg.initialize()
    #Trade.initialize()
    #print(Trade.get_collateral())
    #test = Trade.cancel_and_wait_completion('test')
    #print(Trade.get_order_status('test'))

    '''
    Trade.initialize()
    oid = Trade.order('buy', 500000, 0.1, 1)
    print(Trade.get_order_status(oid))
    time.sleep(3)
    print(Trade.get_order_status(oid)[0])
    Trade.cancel_order(oid)
    time.sleep(5)
    print(Trade.get_order_status(oid)[0])
    '''





