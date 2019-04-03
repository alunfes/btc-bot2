import threading
import pandas as pd
import time
import copy
from datetime import datetime
from OneMinutesData import OneMinutesData
from CryptowatchDataGetter import CryptowatchDataGetter
from SystemFlg import SystemFlg


class MarketData:
    @classmethod
    def initialize_for_sim(cls, max_term, future_side_period, future_side_kijun):
        cls.max_term = max_term + 5
        cls.future_side_period = future_side_period
        cls.future_side_kijun = future_side_kijun
        cls.data_lock = threading.Lock()

        cls.ohlc_data = OneMinutesData()
        cls.ohlc_data.initialize()
        cls.ohlc_data = cls.read_from_csv(cls.ohlc_data)

        cls.calc_all_ma(cls.ohlc_data)
        cls.calc_all_ma_kairi(cls.ohlc_data)
        cls.calc_all_rsi(cls.ohlc_data)
        cls.calc_all_momentum(cls.ohlc_data)
        cls.calc_future_side(cls.future_side_period, cls.future_side_kijun, cls.ohlc_data)


    @classmethod
    def initialize_for_bot(cls, max_term=110):
        cls.ohlc_bot


    @classmethod
    def set_current_ws_data(cls, data):
        with cls.current_ws_data_lock:
            data['dt'] = datetime.now()
            cls.current_ws_data = data

    @classmethod
    def get_current_ws_data(cls):
        return copy.deepcopy(cls.current_ws_data)

    @classmethod
    def start_marketdata_thread(cls):
        th = threading.Thread(target=cls.update_tmp_ohlc)
        th2 = threading.Thread(target=cls.update_cryptow_data)
        th3 = threading.Thread(target=cls.calc_all_index_for_online_bot)
        th.start()
        th2.start()
        time.sleep(10)
        th3.start()

    '''
    ＊cryptowatchのデータが1分以上前が最新の場合を想定する必要がある。
    
    00秒からのtickを保存しておいて、それを対象にohlc計算する。次の00秒以降になったら、リセット
    ohlc計算は常に00秒からのtickデータを対象にする。->毎回全データを対象にmax, min計算？->追加されたデータだけを対象にするには、更新タイミングを同期しないといけない。
    
    常に数十分くらいのtickを保存しておいて、それを使ってdatetime.now基準でohlcを計算する。
    
    
    cryptowatchで更新した時刻以降のtick dataを対象にohlc計算実施しないといけない。
    00:30-crypto 更新
    00:35-ohlc更新開始　（この時点では最初の30秒間のtickデータがない）
    01:30-ohlc更新開始　（この時点では）
    01:30-crypto 更新
    '''
    @classmethod
    def update_tmp_ohlc(cls):
        while SystemFlg.get_system_flg():
            with cls.data_lock:
                data = cls.get_current_ws_data()
                ind = len(cls.ohlc_data.close) - 1
                if cls.ohlc_data.open[ind] == 0:
                    cls.ohlc_data.open[ind] = data['price']
                cls.ohlc_data.high[ind] = max(cls.ohlc_data.high[ind], data['price'])
                cls.ohlc_data.low[ind] = min(cls.ohlc_data.low[ind], data['price'])
                cls.ohlc_data.close[ind] = data['price']
                cls.ohlc_data.size[ind] += data['size']
                cls.ohlc_data.dt[ind] = datetime.now()
                print('dt={},open={},high={},low={},close={}'.format(cls.ohlc_data.dt[ind],
                                                                     cls.ohlc_data.open[ind],
                                                                     cls.ohlc_data.high[ind],
                                                                     cls.ohlc_data.low[ind],
                                                                     cls.ohlc_data.close[ind]))
            time.sleep(1)

    @classmethod
    def calc_all_index_for_online_bot(cls):
        while SystemFlg.get_system_flg():
            with cls.data_lock:
                cls.calc_all_ma_latest()
                cls.calc_all_ma_kairi_latest()
                cls.calc_all_rsi_latest()
                cls.calc_all_momentum_latest()
                print('ma5={},kairi5={},rsi5={},mom5={}'.format(cls.ohlc_data.ma[5],
                                                                cls.ohlc_data.ma_kairi[5],
                                                                cls.ohlc_data.rsi[5],
                                                                cls.ohlc_data.momentum[5]))
            time.sleep(1)

    @classmethod
    def update_cryptow_data(cls):
        while SystemFlg.get_system_flg():
            if datetime.now().second >= 40:
                #get data from cryptowatch
                df = CryptowatchDataGetter.get_and_add_to_csv()
                if df.shape[0] >0:
                    with cls.data_lock:
                        #check and decide copy area
                        start_ind = -1
                        for i in range(len(df['unix_time'])):
                            if df['unix_time'][i] > cls.ohlc_data.unix_time[len(cls.ohlc_data.unix_time)-1]:
                                start_ind = i
                                break
                        #copy data from df to ohlc
                        if start_ind != -1:
                            cls.ohlc_data.dt.extend(list(df['dt'][start_ind:]))
                            cls.ohlc_data.unix_time.extend(list(df['unix_time'][start_ind:]))
                            cls.ohlc_data.open.extend(list(df['open'][start_ind:]))
                            cls.ohlc_data.high.extend(list(df['high'][start_ind:]))
                            cls.ohlc_data.low.extend(list(df['low'][start_ind:]))
                            cls.ohlc_data.close.extend(list(df['close'][start_ind:]))
                            cls.ohlc_data.size.extend(list(df['size'][start_ind:]))
                            #append tmp val
                            cls.ohlc_data.dt.append(0)
                            cls.ohlc_data.unix_time.append(0)
                            cls.ohlc_data.open.append(0)
                            cls.ohlc_data.high.append(0)
                            cls.ohlc_data.low.append(0)
                            cls.ohlc_data.close.append(0)
                            cls.ohlc_data.size.append(0)
                            print('updated crypto watch data - '+str(datetime.now()))
                    time.sleep(20)
                time.sleep(1)

    @classmethod
    def read_from_csv(cls, ohlc):
        with cls.data_lock:
            ohlc.initialize()
            df = CryptowatchDataGetter.read_csv_data()
            ohlc.dt = list(df['dt'])
            ohlc.unix_time = list(df['unix_time'])
            ohlc.open = list(df['open'])
            ohlc.high = list(df['high'])
            ohlc.low = list(df['low'])
            ohlc.close = list(df['close'])
            ohlc.size = list(df['size'])
            return ohlc
            #cls.ohlc_data.size = dict(zip(range(0, len(list(df['size']))), list(df['size'])))

    #can't use for online prediction, missed for latest data for future_side_period
    @classmethod
    def generate_df(cls):
        with cls.data_lock:
            end = len(cls.ohlc_data.close) - cls.future_side_period
            df = pd.DataFrame()
            df = df.assign(dt=cls.ohlc_data.dt[cls.max_term:end])
            df = df.assign(open=cls.ohlc_data.open[cls.max_term:end])
            df = df.assign(high=cls.ohlc_data.high[cls.max_term:end])
            df = df.assign(low=cls.ohlc_data.low[cls.max_term:end])
            df = df.assign(close=cls.ohlc_data.close[cls.max_term:end])
            df = df.assign(size=cls.ohlc_data.size[cls.max_term:end])
            for k in cls.ohlc_data.ma_kairi:
                col = 'ma_kairi' + str(k)
                df = df.assign(col=cls.ohlc_data.ma_kairi[k][cls.max_term:end])
                df.rename(columns={'col':col}, inplace = True)
            for k in cls.ohlc_data.rsi:
                col = 'rsi' + str(k)
                df = df.assign(col=cls.ohlc_data.rsi[k][cls.max_term:end])
                df.rename(columns={'col': col}, inplace=True)
            for k in cls.ohlc_data.momentum:
                col = 'mom' + str(k)
                df = df.assign(col=cls.ohlc_data.momentum[k][cls.max_term:end])
                df.rename(columns={'col': col}, inplace=True)
            df = df.assign(future_side=cls.ohlc_data.future_side[cls.max_term:])
        return df

    @classmethod
    def generate_df_for_bot_predict(cls):
        with cls.data_lock:
            df = pd.DataFrame()
            for k in cls.ohlc_data.ma_kairi:
                col = 'ma_kairi' + str(k)
                li = list(cls.ohlc_data.ma_kairi[k])
                df = df.assign(col=li[len(li)-1])
                df.rename(columns={'col': col}, inplace=True)
            for k in cls.ohlc_data.rsi:
                col = 'rsi' + str(k)
                li = list(cls.ohlc_data.rsi[k].values())
                df = df.assign(col=li[len(li)-1])
                df.rename(columns={'col': col}, inplace=True)
            for k in cls.ohlc_data.momentum:
                col = 'mom' + str(k)
                li = list(cls.ohlc_data.momentum[k].values())
                df = df.assign(col=li[len(li)-1])
                df.rename(columns={'col': col}, inplace=True)
        return df

    @classmethod
    def generate_df_for_bot_train(cls, max_term, future_side_period, future_side_kijun):
        cls.max_term = max_term + 5
        cls.future_side_period = future_side_period
        cls.future_side_kijun = future_side_kijun

        cls.ohlc_bot = OneMinutesData()
        cls.ohlc_bot.initialize()
        cls.ohlc_bot = cls.read_from_csv(cls.ohlc_bot)

        cls.calc_all_ma(cls.ohlc_bot)
        cls.calc_all_ma_kairi(cls.ohlc_bot)
        cls.calc_all_rsi(cls.ohlc_bot)
        cls.calc_all_momentum(cls.ohlc_bot)
        cls.calc_future_side(cls.future_side_period, cls.future_side_kijun, cls.ohlc_bot)

        end = len(cls.ohlc_bot.close) - cls.future_side_period
        df = pd.DataFrame()
        df = df.assign(dt=cls.ohlc_bot.dt[cls.max_term:end])
        df = df.assign(open=cls.ohlc_bot.open[cls.max_term:end])
        df = df.assign(high=cls.ohlc_bot.high[cls.max_term:end])
        df = df.assign(low=cls.ohlc_bot.low[cls.max_term:end])
        df = df.assign(close=cls.ohlc_bot.close[cls.max_term:end])
        df = df.assign(size=cls.ohlc_bot.size[cls.max_term:end])
        for k in cls.ohlc_bot.ma_kairi:
            col = 'ma_kairi' + str(k)
            df = df.assign(col=list(cls.ohlc_bot.ma_kairi[k].values())[cls.max_term:end])
            df.rename(columns={'col': col}, inplace=True)
        for k in cls.ohlc_bot.rsi:
            col = 'rsi' + str(k)
            df = df.assign(col=list(cls.ohlc_bot.rsi[k].values())[cls.max_term:end])
            df.rename(columns={'col': col}, inplace=True)
        for k in cls.ohlc_bot.momentum:
            col = 'mom' + str(k)
            df = df.assign(col=list(cls.ohlc_bot.momentum[k].values())[cls.max_term:end])
            df.rename(columns={'col': col}, inplace=True)
        df = df.assign(future_side=list(cls.ohlc_bot.future_side.values())[cls.max_term:])
        return df



    @classmethod
    def calc_future_side(cls, future_side_period, future_side_kijun, ohlc):
        for i in range(len(ohlc.close) - future_side_period):
            buy_max = 0
            sell_max = 0
            for j in range(i, i + future_side_period):
                buy_max = max(buy_max, ohlc.close[j] - ohlc.close[i])
                sell_max = max(sell_max, ohlc.close[i] - ohlc.close[j])
            if buy_max >= future_side_kijun and sell_max >= future_side_kijun:
                ohlc.future_side.append('both')
            elif buy_max >= future_side_kijun and sell_max < future_side_kijun:
                ohlc.future_side.append('buy')
            elif buy_max < future_side_kijun and sell_max >= future_side_kijun:
                cls.ohlc_data.future_side.append('sell')
            elif buy_max < future_side_kijun and sell_max < future_side_kijun:
                cls.ohlc_data.future_side.append('no')


    @classmethod
    def calc_ma(cls, term, ohlc:OneMinutesData):
        sum = 0
        ma = []
        for i in range(term):
            sum += ohlc.close[i]
            ma.append(0)
        ma.pop(0)
        ma.append(float(sum) / float(term))
        for i in range(len(ohlc.close) - term):
            ind = i + term
            sum = sum - ohlc.close[ind-term] + ohlc.close[ind]
            ma.append(float(sum) / float(term))
        return ma


    @classmethod
    def calc_all_ma(cls, ohlc):
        for i in range(cls.max_term - 5):
            ind = i + 5
            ohlc.ma[ind] = cls.calc_ma(ind, ohlc)

    @classmethod
    def calc_ma_latest(cls, term):
        return float(sum(cls.ohlc_data.close[len(cls.ohlc_data.close) - term:])) / float(term)

    @classmethod
    def calc_all_ma_latest(cls):
        for i in range(cls.max_term - 5):
            ind = i + 5
            cls.ohlc_data.ma[ind] = cls.calc_ma_latest(ind)

    @classmethod
    def calc_ma_kairi_latest(cls, term):
        return cls.ohlc_data.close[len(cls.ohlc_data.close)-1] / cls.ohlc_data.ma[term]

    @classmethod
    def calc_all_ma_kairi_latest(cls):
        for i in range(cls.max_term - 5):
            ind = i + 5
            cls.ohlc_data.ma_kairi[ind] = cls.calc_ma_kairi_latest(ind)


    @classmethod
    def calc_ma_kairi(cls, term, ohlc):
        kairi = []
        for i in range(len(ohlc.ma[term])):
            if ohlc.ma[term][i] == 0:
                kairi.append(0)
            else:
                kairi.append(ohlc.close[i] / ohlc.ma[term][i])
        return kairi

    @classmethod
    def calc_all_ma_kairi(cls, ohlc):
        for i in range(cls.max_term -5):
            ind = i+5
            ohlc.ma_kairi[ind] = cls.calc_ma_kairi(ind, ohlc)

    @classmethod
    def calc_rsi(cls, term, ohlc):
        up_sum = 0
        down_sum = 0
        rsi = []
        for i in range(term):
            rsi.append(0)
        for i in range(term, len(ohlc.close)):
            up_sum = 0
            down_sum = 0
            for j in range(term):
                change = ohlc.close[i-j] - ohlc.open[i-j]
                if change >= 0:
                    up_sum += change
                else:
                    down_sum += abs(change)
            if up_sum ==0 and down_sum == 0:
                rsi.append(0)
            else:
                rsi.append(up_sum/(up_sum + down_sum))
        return rsi

    @classmethod
    def calc_all_rsi(cls, ohlc):
        for i in range(cls.max_term-5):
            ind = i + 5
            ohlc.rsi[ind] = cls.calc_rsi(ind, ohlc)

    @classmethod
    def calc_rsi_latest(cls, term):
        up_sum = 0
        down_sum = 0
        rsi = 0
        ind = len(cls.ohlc_data.close)-1
        for i in range(term):
            change = cls.ohlc_data.close[ind - i] - cls.ohlc_data.open[ind - i]
            if change >= 0:
                up_sum += change
            else:
                down_sum += abs(change)
        if up_sum == 0 and down_sum == 0:
            rsi = 0
        else:
            rsi = up_sum / (up_sum + down_sum)
        return rsi

    @classmethod
    def calc_all_rsi_latest(cls):
        for i in range(cls.max_term - 5):
            ind = i + 5
            cls.ohlc_data.rsi[ind] = cls.calc_rsi_latest(ind)

    @classmethod
    def calc_momentum(cls,term, ohlc):
        mom = []
        for i in range(term):
            mom.append(0)
        for i in range(term, len(ohlc.close)):
            mom.append(ohlc.close[i] - ohlc.close[i-term])
        return mom

    @classmethod
    def calc_all_momentum(cls, ohlc):
        for i in range(cls.max_term-5):
            ind = i +5
            ohlc.momentum[ind] = cls.calc_momentum(ind, ohlc)

    @classmethod
    def calc_momentum_latest(cls, term):
        return cls.ohlc_data.close[len(cls.ohlc_data.close)-1] - cls.ohlc_data.close[len(cls.ohlc_data.close)-1-term]

    @classmethod
    def calc_all_momentum_latest(cls):
        for i in range(cls.max_term - 5):
            ind = i + 5
            cls.ohlc_data.momentum[ind] = cls.calc_momentum_latest(ind)


if __name__ == '__main__':
    print('')