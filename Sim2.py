from Account2 import Account2
from MarketData3 import MarketData3
import random
from CatModel import CatModel


class Sim2:
    @classmethod
    def start_sim(cls,test_x, prediction, pl_kijun, kairi_suspension_kijun, conservertive_trade, ohlc):
        cls.ac = Account2()
        cls.start_ind = cls.check_matched_index(test_x,ohlc)
        cls.tick, cls.pred = MarketData3.generate_tick_pred_data(ohlc, prediction, cls.start_ind)
        cls.pred = cls.__pred_converter(cls.pred)
        cls.prediction_delay = 3
        for i in range(len(cls.pred) - 1):
            '''
            1.no position & no order & prediction
            2.no position and order side = prediction
            3.no position and order side != prediction
            4.position side == prediction & no order -> entry pl order
            5.position side == prediction & order side == prediction -> cancel order (既にpredと同じsideのポジ持ってるのに、同一方向のオーダーがある)
            6.position side == prediction & order side != prediction ->do nothing (既にポジションとpl orderがある)
            7.position side != prediction & no order ->exit order and entry to prediction side
            8.position side != prediction & order side != position side & order size == self.holding_size -> cancel order (holding position and pl ordering)
            9.position side != prediction & order side != prediction -> pass ()
            '''
            '''
            flg_entry = False
            flg_exit = False
            if conservertive_trade:
                
            else:
            '''
            if conservertive_trade:
                if cls.ac.holding_side == '' and cls.ac.order_side == '' and (cls.pred[i] == 'buy' or cls.pred[i] == 'sell'): #1
                    cls.ac.entry_order(cls.pred[i], 0, cls.__calc_opt_size(cls.tick[i]), 'market', 60, i)
                elif cls.ac.holding_side == '' and ((cls.ac.order_side != cls.pred[i]) or (cls.ac.order_side == cls.pred[i])): #2
                    pass
                elif cls.ac.holding_side == '' and cls.ac.order_side != cls.pred[i]: #3
                    cls.ac.cancel_order(i)
                elif cls.ac.holding_side !='' and not(cls.pred[i] == 'buy' and cls.ac.holding_side=='sell') and not(cls.pred[i] == 'sell' and cls.ac.holding_side=='buy') and cls.ac.order_side =='': #4
                    price = cls.ac.holding_price + pl_kijun if cls.ac.holding_side == 'buy' else cls.ac.holding_price - pl_kijun
                    cls.ac.entry_order('buy' if cls.ac.holding_side=='sell' else 'sell', price, cls.ac.holding_size, 'limit',1440, i)
                elif cls.ac.holding_side != '' and (cls.ac.holding_side == cls.ac.order_side):  # 5
                    cls.ac.cancel_order(i)
                elif cls.ac.holding_side == cls.pred[i] and cls.ac.order_side != cls.pred[i]:  # 6
                    pass
                elif cls.ac.holding_side != cls.pred[i] and cls.ac.order_side =='': #7
                    cls.ac.entry_order(cls.pred[i], 0, cls.ac.holding_size * 2, 'market', 60, i)
                elif cls.ac.holding_side != cls.pred[i] and cls.ac.order_side != cls.ac.holding_side and cls.ac.order_size == cls.ac.holding_size: #8
                    cls.ac.cancel_order(i)
                elif cls.ac.holding_side != '' and (cls.pred[i] == 'buy' or cls.pred[i] == 'sell') and cls.ac.holding_side != cls.pred[i] and cls.ac.order_side != cls.pred[i]:  # 9
                    print('unexpected situation in sim!')
                    print('position:' + cls.ac.holding_side + ', ' + str(cls.ac.holding_size) + ', order:' + cls.ac.order_side + ', ' + str(cls.ac.order_size) + ', pred=' +cls.pred[i])
                    pass
                else:
                    pass
                    #print('hside={},hsize={},oside={},osize={}'.format(cls.ac.holding_side,cls.ac.holding_size,cls.ac.order_side,cls.ac.order_size))
            else:
                if cls.ac.holding_side =='' and cls.ac.order_side == '' and (cls.pred[i] == 'buy' or cls.pred[i] == 'sell'): #1
                    print(str(i) + ': new entry, ' + cls.pred[i])
                    cls.ac.entry_order(cls.pred[i], 0, cls.__calc_opt_size(cls.tick[i]), 'market', 60, i)
                elif cls.ac.holding_side =='' and ((cls.ac.order_side == 'buy' and cls.pred[i]!='sell') or (cls.ac.order_side == 'sell' and cls.pred[i]!='buy')): #2
                    pass
                elif cls.ac.holding_side =='' and ((cls.ac.order_side == 'buy' and cls.pred[i] == 'sell') or (cls.ac.order_side == 'sell' and cls.pred[i] == 'buy')) and cls.ac.order_cancel == False: #3
                    print(str(i) + ': No position, order side and prediciton unmatched then cancel order. ')
                    cls.ac.cancel_order(i)
                elif cls.ac.holding_side !='' and not(cls.pred[i] == 'buy' and cls.ac.holding_side=='sell') and not(cls.pred[i] == 'sell' and cls.ac.holding_side=='buy') and cls.ac.order_side =='': #4
                    price = cls.ac.holding_price + pl_kijun if cls.ac.holding_side == 'buy' else cls.ac.holding_price - pl_kijun
                    print(str(i) + ':Entry pl order. @' + str(price))
                    cls.ac.entry_order('buy' if cls.ac.holding_side=='sell' else 'sell', price, cls.ac.holding_size, 'limit',1440, i)
                elif cls.ac.holding_side != '' and (cls.ac.holding_side == cls.ac.order_side)  and cls.ac.order_cancel == False:  # 5
                    cls.ac.cancel_order(i)
                    print(str(i) + ':既にpredと同じsideのポジ持ってるのに、同一方向のオーダーがある')
                elif (cls.ac.holding_side == cls.pred[i] and cls.ac.holding_side != cls.pred[i]):  # 6
                    pass
                elif cls.ac.holding_side != '' and (cls.pred[i] == 'buy' or cls.pred[i] == 'sell') and cls.ac.holding_side != cls.pred[i] and cls.ac.order_side =='': #7
                    print(str(i) + ':Opposite prediction and no order. Entry exit order.')
                    cls.ac.entry_order(cls.pred[i], 0, cls.ac.holding_size * 2, 'market', 60, i)
                elif (cls.pred[i] == 'buy' or cls.pred[i] == 'sell') and  cls.ac.holding_side != cls.pred[i] and cls.ac.order_side != cls.ac.holding_side and cls.ac.order_size == cls.ac.holding_size  and cls.ac.order_cancel == False: #8
                    print(str(i) + ':Opposite prediction then cancel pl order.')
                    cls.ac.cancel_order(i)
                elif cls.ac.holding_side != '' and (cls.pred[i] == 'buy' or cls.pred[i] == 'sell') and cls.ac.holding_side != cls.pred[i] and cls.ac.order_side != cls.pred[i]:  # 9
                    print('unexpected situation in sim!')
                    print('position:' + cls.ac.holding_side + ', ' + str(cls.ac.holding_size) + ', order:' + cls.ac.order_side + ', ' + str(cls.ac.order_size) + ', pred=' +cls.pred[i])
                    pass
                else:
                    pass
                    #print('hside={},hsize={},oside={},osize={}'.format(cls.ac.holding_side,cls.ac.holding_size,cls.ac.order_side,cls.ac.order_size))
            cls.ac.move_to_next(i,cls.tick[i])
        cls.ac.last_day_operation(len(cls.pred)-1, cls.tick[-1])
        return (cls.ac.total_pl,cls.ac.num_trade,cls.ac.win_rate,cls.ac.total_pl_log)


    @classmethod
    def check_matched_index(cls, test_x, ohlc):
        key = list(ohlc.ema_kairi.keys())[0]
        test = list(test_x['ema_kairi' + str(key)])
        kairi = ohlc.ema_kairi[key]
        for i in range(len(kairi)):
            flg = True
            for j in range(30):
                if test[j] != kairi[i+j]:
                    flg = False
                    break
            if flg:
                return i
        return -1

    @classmethod
    def __calc_opt_size(cls, price):
        return round((cls.ac.asset * cls.ac.leverage) / (price * 1.0 * cls.ac.base_margin_rate), 2)

    @classmethod
    def __pred_converter(cls, prediction): #convert prediction(-1-3) to prediction('', no, buy, sell, both)
        def __converter(d):
            if d == -1:
                return ''
            elif d == 0:
                return 'no'
            elif d == 1:
                return 'buy'
            elif d == 2:
                return 'sell'
            elif d == 3:
                return 'both'
            else:
                print('unknown prediction value in sim2!')
                return 'error'
        return list(map(__converter, prediction))


if __name__ == '__main__':
    MarketData3.initialize_for_bot(1000, 10, 30, 1000, 3000)
    df = MarketData3.generate_df()
    model = CatModel()
    train_x, test_x, train_y, test_y = model.generate_data(df, 0.05)
    train_xx = train_x
    train_yy = train_y
    test_xx = test_x
    test_yy = test_y

    l = [0, 1, 2, 3]
    pred = []
    for p in range(len(test_yy)):
        pred.append(random.choice(l))

    res = Sim2.start_sim(test_xx, pred, 1000, 1.0, False, MarketData3.ohlc)
