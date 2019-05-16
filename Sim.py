from MarketData2 import MarketData2
from CatModel import CatModel
from Account import Account
from catboost import Pool

class Sim:
    @classmethod
    def check_matched_index(cls, test_x):
        key = list(cls.ohlc.ma_kairi.keys())[0]
        test = list(test_x['ma_kairi' + str(key)])
        kairi = cls.ohlc.ma_kairi[key]
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
    def __calc_opt_size(cls, ind):
        return round((cls.asset * cls.leverage) / (cls.ohlc.close[ind] * 1.0 * cls.base_margin_rate),2)

    @classmethod
    def __initialize_posi(cls):
        cls.posi_side  =''
        cls.posi_price = 0
        cls.posi_size = 0
    
    @classmethod
    def __add_log(cls, log, ind, i):
        cls.trade_log.append(log)
        cls.trade_log_i.append(i)
        print('i={},: {}'.format(i,log))
        

    @classmethod
    def simple_sim(cls, test_x, prediction, pl_kijun, kairi_suspension_kijun, conservertive_trade, ohlc):
        cls.base_margin_rate = 1.2
        cls.leverage = 15.0
        cls.slip_page = 500
        cls.force_loss_cut_rate = 0.5
        cls.initial_asset = 5000
        cls.asset = cls.initial_asset
        cls.__initialize_posi()
        
        cls.pl_kijun = pl_kijun

        cls.total_pl = 0
        cls.holding_pl = 0
        cls.realized_pl = 0
        cls.num_trade = 0
        cls.num_win = 0
        cls.win_rate = 0
        cls.total_pl_log= []
        cls.ohlc = ohlc

        cls.trade_log = []
        cls.trade_log_i = []

        start_ind = cls.check_matched_index(test_x)
        for i in range(len(prediction) - 1):
            ind = i + start_ind
            if cls.posi_side == '':
                if prediction[i] == 1 or prediction[i] == 2:
                    cls.__entry_order('buy' if prediction[i]==1 else 'sell',cls.__calc_opt_size(ind),cls.ohlc.open[ind+1],ind,i)
            elif cls.posi_side == 'buy' or cls.posi_side == 'sell':
                if (cls.posi_side == 'buy' and prediction[i] != 2) or (cls.posi_side == 'sell' and prediction[i] != 1):
                    cls.__check_pl_execution(ind, i)
                elif (cls.posi_side == 'buy' and prediction[i] == 2) or (cls.posi_side == 'sell' and prediction[i] == 1):
                    cls.__price_tracing_exit(ind+1,i+1)
                    p=0
                    if cls.ohlc.open[ind] > cls.ohlc.close[ind]: #open, low, high, close
                        p = (cls.ohlc.low[ind+1] + cls.ohlc.open[ind+1]) * 0.5
                    else:#open, high, low, close
                        p = (cls.ohlc.high[ind+1] + cls.ohlc.open[ind+1]) * 0.5
                    cls.__entry_order('sell',cls.__calc_opt_size(ind+1),p,ind,i+1)
                else:
                    print('unhandled case!!!!')
            cls.holding_pl = round((cls.ohlc.close[ind] - cls.posi_price ) * cls.posi_size) if cls.posi_side == 'buy' else round((cls.posi_price - cls.ohlc.close[ind]) * cls.posi_size)
            cls.total_pl = cls.realized_pl + cls.holding_pl
            cls.total_pl_log.append(cls.total_pl)
            cls.__add_log('i='+str(i)+', posi_side='+cls.posi_side+', price='+str(cls.posi_price)+', size='+str(cls.posi_size)+', total pl ='+str(cls.total_pl),ind,i)
            cls.__add_log('ohlc:'+str(cls.ohlc.open[ind])+' '+str(cls.ohlc.high[ind])+' '+str(cls.ohlc.low[ind])+' '+str(cls.ohlc.close[ind]),ind,i)
            cls.__add_log('prediction='+str(prediction[i]),ind,i)
        cls.__add_log('last:'+'total pl ='+str(cls.total_pl)+', num trade='+str(cls.num_trade)+', win rate='+str(cls.win_rate),ind,i)
        return (cls.total_pl,cls.num_trade,cls.win_rate,cls.total_pl_log) #(cls.ac.total_pl, cls.ac.num_trade, cls.ac.win_rate, cls.ac.total_pl_log)
            
    @classmethod
    def __check_pl_execution(cls, ind, i):
        if cls.ohlc.open[ind] > cls.ohlc.close[ind]: #open, low, high, close
            if cls.posi_side != '':
                if cls.posi_side =='sell' or (cls.posi_side =='buy' and cls.__check_and_do_force_loss_cut(ind,i) == False):
                    if (cls.posi_price + cls.pl_kijun <= cls.ohlc.high[ind] and cls.posi_side == 'buy') or (cls.posi_price - cls.pl_kijun >= cls.ohlc.low[ind] and cls.posi_side == 'sell'): #in case pl executed
                        mul = (cls.ohlc.high[ind] - cls.posi_price) / cls.pl_kijun if cls.posi_side == 'buy' else (cls.posi_price - cls.ohlc.low[ind]) / cls.pl_kijun
                        pl = cls.pl_kijun * cls.posi_size + round((mul -1) * cls.pl_kijun * 0.5 * cls.posi_size)
                        num = 1 + round((mul-1) * 0.5)
                        cls.realized_pl += pl
                        cls.num_trade += num
                        cls.num_win += num
                        cls.posi_price = cls.ohlc.high[ind] - round(cls.pl_kijun * 0.5) if cls.posi_side == 'buy' else cls.ohlc.low[ind] + round(cls.pl_kijun * 0.5)
                        cls.__add_log('pl executed, pl='+str(pl)+', num='+str(num)+', new entry price='+str(cls.posi_price),ind,i)
                        return True
                    else:
                        if cls.posi_side =='sell':
                            cls.__check_and_do_force_loss_cut(ind,i)
        else:#open, high, low, close
            if cls.posi_side != '':
                if cls.posi_side =='buy' or (cls.posi_side =='sell' and cls.__check_and_do_force_loss_cut(ind,i) == False):
                    if (cls.posi_price + cls.pl_kijun <= cls.ohlc.high[ind] and cls.posi_side == 'buy') or (cls.posi_price - cls.pl_kijun >= cls.ohlc.low[ind] and cls.posi_side == 'sell'): #in case pl executed
                        mul = (cls.ohlc.high[ind] - cls.posi_price) / cls.pl_kijun if cls.posi_side == 'buy' else (cls.posi_price - cls.ohlc.low[ind]) / cls.pl_kijun
                        pl = cls.pl_kijun * cls.posi_size + round((mul -1) * cls.pl_kijun * 0.5 * cls.posi_size)
                        num = 1 + round((mul-1) * 0.5)
                        cls.realized_pl += pl
                        cls.num_trade += num
                        cls.num_win += num
                        cls.posi_price = cls.ohlc.high[ind] - round(cls.pl_kijun * 0.5) if cls.posi_side == 'buy' else cls.ohlc.low[ind] + round(cls.pl_kijun * 0.5)
                        cls.__add_log('pl executed, pl='+str(pl)+', num='+str(num)+', new entry price='+str(cls.posi_price),ind,i)
                        return True
                    else:
                        if cls.posi_side =='sell':
                            cls.__check_and_do_force_loss_cut(ind,i)
        return False
            
    @classmethod
    def __check_and_do_force_loss_cut(cls, ind, i):
        if cls.posi_size > 0:
            req_collateral = cls.posi_size * cls.ohlc.close[ind] / cls.leverage
            pl = (cls.ohlc.low[ind] - cls.posi_price) if cls.posi_side == 'buy' else (cls.posi_price - cls.ohlc.high[ind])
            pl = pl * cls.posi_size
            margin_rate = (cls.initial_asset+cls.realized_pl+pl) / req_collateral
            if margin_rate <= cls.force_loss_cut_rate:
                cls.realized_pl += (cls.ohlc.low[ind] - cls.posi_price) * cls.posi_size if cls.posi_side == 'buy' else (cls.posi_price - cls.ohlc.high[ind]) * cls.posi_size
                cls.num_trade += 1
                cls.__initialize_posi()
                cls.__add_log('loss cut, pl='+str(pl)+', margin_rate='+str(margin_rate),ind,i)
                return True
        return False

    @classmethod
    def __entry_order(cls, side, size, price,ind,i):
        cls.__add_log('entry order, '+'side='+side+', price='+str(price)+', size='+str(size),ind,i)
        cls.posi_side = side
        cls.posi_price = price
        cls.posi_size = size
    
    @classmethod
    def __price_tracing_exit(cls, ind ,i):
        p = 0
        pl = 0
        if cls.ohlc.open[ind] > cls.ohlc.close[ind]: #open, low, high, close
            p = (cls.ohlc.low[ind] + cls.ohlc.open[ind]) * 0.5
            pl = round((p - cls.posi_price) * cls.posi_size) if cls.posi_side == 'buy' else round((cls.posi_price - p) * cls.posi_size)
        else:#open, high, low, close
            p = (cls.ohlc.high[ind] + cls.ohlc.open[ind]) * 0.5
            pl = round((p - cls.posi_price) * cls.posi_size) if cls.posi_side == 'buy' else round((cls.posi_price - p) * cls.posi_size)
        cls.realized_pl += pl
        cls.num_trade +=1
        if pl > 0:
            cls.num_win += 1
        cls.__add_log('exited position-'+'exited price='+str(p)+', pl='+str(pl),ind,i)
        cls.__initialize_posi()





    @classmethod
    def entry_order(cls, prediction, pl_kijun, ind, i):
        if prediction == 1:
            cls.ac.entry_order('buy', cls.ohlc.close[ind], cls.ac.calc_opt_size(ind), 'new IFD entry',1, True, pl_kijun, ind, i)
        elif prediction == 2:
            cls.ac.entry_order('sell',cls.ohlc.close[ind], cls.ac.calc_opt_size(ind), 'new IFD entry',1, True, pl_kijun, ind, i)

    @classmethod
    def start_sim(cls, test_x, prediction, pl_kijun, kairi_suspension_kijun, conservertive_trade, ohlc):
        cls.ac = Account(pl_kijun)
        cls.ohlc = ohlc
        start_ind = cls.check_matched_index(test_x)
        for i in range(len(prediction) - 1):
            ind = i + start_ind
            if cls.ac.holding_side == '' and len(cls.ac.unexe_side) == 0 and abs(1.00 - cls.ohlc.ma_kairi[5][ind]) < kairi_suspension_kijun:
                cls.entry_order(prediction[i],pl_kijun,ind,i)
            if conservertive_trade:
                # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。
                if (cls.ac.holding_side == 'buy' and (prediction[i] == 2 or prediction[i] == 3)) or \
                        (cls.ac.holding_side == 'sell' and (prediction[i] == 1 or prediction[i] == 3)):
                    for k in cls.ac.unexe_side.keys():
                        cls.ac.cancel_order(k,ind,i)
                    cls.ac.exit_all_positions(ind, i)
                    cls.entry_order(prediction[i],pl_kijun,ind,i)
                # ノーポジでオーダーが判定と逆の時にキャンセル。
                if len(cls.ac.unexe_side) == 0:
                    for k in cls.ac.unexe_side.keys():
                        if (cls.ac.unexe_side[k] == 'buy' and (prediction[i] == 2 or prediction[i] == 3))or (
                                cls.ac.unexe_side[k] == 'sell' and (prediction[i] == 1 or prediction[i] == 2)):
                            cls.ac.cancel_order(k, ind, i)
                            cls.entry_order(prediction[i],pl_kijun,ind,i)
            elif conservertive_trade == False: #non conservertive trade
                # ポジションが判定と逆の時にexit,　もしplがあればキャンセル。
                if (cls.ac.holding_side == 'buy' and prediction[i] == 2) or \
                        (cls.ac.holding_side == 'sell' and prediction[i] == 1):
                    for k in cls.ac.unexe_side.keys():
                        cls.ac.cancel_order(k,ind,i)
                    cls.ac.exit_all_positions(ind, i)
                    cls.entry_order(prediction[i],pl_kijun,ind,i)
                #ノーポジでオーダーが判定を逆の時にキャンセル。
                if len(cls.ac.unexe_side) == 0:
                    for k in cls.ac.unexe_side.keys():
                        if (cls.ac.unexe_side[k] =='buy' and prediction[i] == 2) or (cls.ac.unexe_side[k] =='sell' and prediction[i] == 1):
                            cls.ac.cancel_order(k,ind,i)
                            cls.entry_order(prediction[i],pl_kijun,ind,i)
            if abs(1.00 - ohlc.ma_kairi[list(ohlc.ma_kairi.keys())[-1]][ind]) >= kairi_suspension_kijun: #kairiが一定以上の時
                if len(cls.ac.unexe_side) == 0:
                    for k in cls.ac.unexe_side.keys():
                        if (cls.ac.unexe_side[k] == 'buy' and prediction[i] == 2) or (
                                cls.ac.unexe_side[k] == 'sell' and prediction[i] == 1):
                            cls.ac.cancel_order(k, ind, i)
            cls.ac.move_to_next(prediction[i],pl_kijun,ind,i)
        cls.ac.last_day_operation(len(prediction)+start_ind-1,len(prediction) - 1)
        return (cls.ac.total_pl, cls.ac.num_trade, cls.ac.win_rate, cls.ac.total_pl_log)


if __name__ == '__main__':
    print('initializing data')
    MarketData2.initialize_from_bot_csv(100,1,30,500,500)
    df =MarketData2.generate_df(MarketData2.ohlc_bot)
    model = CatModel()
    print('init')
    cbm  =model.read_dump_model('./Model/cat_model.dat')
    train_x, test_x, train_y, test_y = model.generate_data(df)
    predict = cbm.predict(Pool(test_x))
    #res = Sim.start_sim(test_x,predict,500,1.0,False,MarketData2.ohlc_bot)
    res = Sim.simple_sim(test_x, predict ,500,1.0,False,MarketData2.ohlc_bot)



