from MarketData2 import  MarketData2
from datetime import datetime
from Account import Account


class Sim:
    @classmethod
    def check_matched_index(cls, test_x):
        key = list(MarketData2.ohlc_bot.ma_kairi.keys())[0]
        test = list(test_x['ma_kairi'+str(key)])
        kairi = cls.data.ma_kairi[key]
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
    def start_sim(cls, test_x, prediction, pl_kijun, kairi_suspension_kijun, conservertive_trade, ohlc):
        cls.ac = Account()
        cls.ohlc = ohlc
        start_ind = cls.check_matched_index(test_x)
        for i in range(len(prediction) - 1):
            ind = i + start_ind
            if cls.ac.holding_side == '' and len(cls.ac.unexe_side) == 0 and abs(1.00 - cls.ohlc.ma_kairi[5][ind]) < kairi_suspension_kijun:
                if prediction[i] == 1:
                    cls.ac.entry_order('buy', cls.ohlc.close[ind], cls.ac.calc_opt_size(ind), ind, i)
                elif prediction[i] == 2:
                    cls.ac.entry_order('sell',cls.ohlc.close[ind], cls.ac.calc_opt_size(ind), ind, i)
            if conservertive_trade:
                # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。
                if (cls.ac.holding_side == 'buy' and (prediction[i] == 2 or prediction[i] == 0 or prediction[i] == 3)) or \
                        (cls.ac.holding_side=='sell' and (prediction[i] == 1 or prediction[i] == 0 or prediction[i] == 3)):
                    cls.ac.cancel_all_orders(ind, i)
                    if cls.ac.holding_side != '':
                        cls.ac.exit_all_positions(ind, i)
                #ノーポジでオーダーが判定を逆の時にキャンセル。
                for j in cls.ac.unexe_side:
                    if (cls.ac.unexe_side[j] == 'buy' and cls.ac.holding_side =='' and (prediction[i] == 2 or prediction[i] == 0 or prediction[i] == 3)) or  (cls.ac.unexe_side[j]=='sell' and cls.ac.holding_side =='' and (prediction[i] == 1 or prediction[i] == 0 or prediction[i] == 3)):
                        cls.ac.cancel_all_orders(ind,i)
            elif conservertive_trade==False: #non conservertive trade
                # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。
                if (cls.ac.holding_side == 'buy' and prediction[i] == 2) or \
                        (cls.ac.holding_side == 'sell' and prediction[i] == 1):
                    cls.ac.cancel_all_orders(ind, i)
                    if cls.ac.holding_side != '':
                        cls.ac.exit_all_positions(ind, i)
                #ノーポジでオーダーが判定を逆の時にキャンセル。
                for j in cls.ac.unexe_side:
                    if (cls.ac.unexe_side[j]  == 'buy' and cls.ac.holding_side=='' and prediction[i] == 2) or (
                            cls.ac.unexe_side[j] == 'sell' and cls.ac.holding_side =='' and prediction[i] == 1):
                        cls.ac.cancel_all_orders(ind,i)
            if abs(1.00 - ohlc.ma_kairi[list(ohlc.ma_kairi.keys())[-1]][ind]) >= kairi_suspension_kijun: #kairiが一定以上の時
                if len(cls.ac.unexe_side) > 0:
                    cls.ac.cancel_all_orders(ind,i)
            if cls.ac.holding_side != '' and len(cls.ac.unexe_side) == 0 and cls.ac.cancel_all_orders_flg == False:
                cls.ac.pl_order(pl_kijun,ind,i)
            cls.ac.move_to_next(ind,i)
        cls.ac.last_day_operation(len(prediction)+start_ind-1,len(prediction) - 1)
        return (cls.ac.total_pl, cls.ac.num_trade, cls.ac.win_rate, cls.ac.total_pl_log)


