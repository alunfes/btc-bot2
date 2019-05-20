from numba import jit, f8, i8, b1, void
from OneMinutesData2 import OneMinutesData2
import numpy as np
import pandas as pd
from multiprocessing import Pool
import talib as ta



'''
using ta-lib for index calc.
'''
class MarketData3:
    @classmethod
    def initialize_for_bot(cls, num_term, window_term, future_side_period, future_side_kijun, initial_data_vol):
        cls.num_term = num_term
        cls.window_term = window_term
        cls.future_side_period = future_side_period
        cls.future_side_kijun = future_side_kijun
        cls.ohlc = cls.read_from_csv('./Data/one_min_data.csv')
        cls.ohlc.del_data(initial_data_vol)
        cls.__calc_all_index(False)

    @classmethod
    def update_for_bot(cls):
        cls.__calc_all_index(True)


    @classmethod
    def read_from_csv(cls, file_name):
        ohlc = OneMinutesData2()
        ohlc.initialize()
        df = pd.read_csv(file_name)
        ohlc.dt = list(df['dt'])
        ohlc.unix_time = list(df['unix_time'])
        ohlc.open = list(df['open'])
        ohlc.high = list(df['high'])
        ohlc.low = list(df['low'])
        ohlc.close = list(df['close'])
        ohlc.size = list(df['size'])
        return ohlc

    @classmethod
    @jit
    def __calc_all_index(cls, flg_for_bot):
        num = round(cls.num_term / cls.window_term)
        if num >1:
            for i in range(num):
                term = cls.window_term * (i+ 1)
                if term > 1:
                    cls.ohlc.ema[term] = cls.__calc_ema(term, cls.ohlc.close)
                    cls.ohlc.ema_kairi[term] = cls.__calc_ema_kairi(term, cls.ohlc.close)
                    cls.ohlc.momentum[term] = cls.__calc_momentum(term, cls.ohlc.close)
                    cls.ohlc.rate_of_change[term] = cls.__calc_rate_of_change(term, cls.ohlc.close)
                    cls.ohlc.rsi[term] = cls.__calc_rsi(term, cls.ohlc.close)
                    cls.ohlc.williams_R[term] = cls.__calc_williams_R(term,cls.ohlc.high, cls.ohlc.low, cls.ohlc.close)
                    cls.ohlc.beta[term] = cls.__calc_beta(term, cls.ohlc.high, cls.ohlc.low)
                    cls.ohlc.tsf[term] = cls.__calc_time_series_forecast(term, cls.ohlc.close)
                    cls.ohlc.correl[term] = cls.__calc_correl(term, cls.ohlc.high, cls.ohlc.low)
        cls.ohlc.normalized_ave_true_range = cls.__calc_normalized_ave_true_range(cls.ohlc.high, cls.ohlc.low, cls.ohlc.close)
        cls.ohlc.three_outside_updown = cls.__calc_three_outside_updown(cls.ohlc.open, cls.ohlc.high, cls.ohlc.low,cls.ohlc.close)
        cls.ohlc.breakway = cls.__calc_breakway(cls.ohlc.open, cls.ohlc.high, cls.ohlc.low, cls.ohlc.close)
        cls.ohlc.dark_cloud_cover = cls.__calc_dark_cloud_cover(cls.ohlc.open, cls.ohlc.high, cls.ohlc.low, cls.ohlc.close)
        cls.ohlc.dragonfly_doji = cls.__calc_dragonfly_doji(cls.ohlc.open, cls.ohlc.high, cls.ohlc.low,cls.ohlc.close)
        cls.ohlc.updown_sidebyside_white_lines = cls.__calc_updown_sidebyside_white_lines(cls.ohlc.open, cls.ohlc.high, cls.ohlc.low, cls.ohlc.close)
        cls.ohlc.haramisen = cls.__calc_haramisen(cls.ohlc.open, cls.ohlc.high,cls.ohlc.low, cls.ohlc.close)
        cls.ohlc.hikkake_pattern = cls.__calc_hikkake_pattern(cls.ohlc.open, cls.ohlc.high, cls.ohlc.low, cls.ohlc.close)
        cls.ohlc.neck_pattern = cls.__calc_neck_pattern(cls.ohlc.open, cls.ohlc.high, cls.ohlc.low,cls.ohlc.close)
        cls.ohlc.upsidedownside_gap_three_method = cls.__calc_upsidedownside_gap_three_method(cls.ohlc.open, cls.ohlc.high, cls.ohlc.low, cls.ohlc.close)
        if flg_for_bot==False:
            cls.ohlc.future_side = cls.calc_future_side(cls.future_side_period,cls.future_side_kijun,cls.ohlc)


    @classmethod
    def generate_df(cls):
        end = len(cls.ohlc.close) - cls.future_side_period
        df = pd.DataFrame()
        df = df.assign(dt=cls.ohlc.dt[cls.num_term:end])
        df = df.assign(open=cls.ohlc.open[cls.num_term:end])
        df = df.assign(high=cls.ohlc.high[cls.num_term:end])
        df = df.assign(low=cls.ohlc.low[cls.num_term:end])
        df = df.assign(close=cls.ohlc.close[cls.num_term:end])
        df = df.assign(size=cls.ohlc.size[cls.num_term:end])
        def __make_col_df(df, data, col_name):
            for k in data:
                col = col_name + str(k)
                df = df.assign(col=data[k][cls.num_term:end])
                df.rename(columns={'col': col}, inplace=True)
                return df
        df = __make_col_df(df, cls.ohlc.ema, 'ema')
        df = __make_col_df(df, cls.ohlc.ema_kairi,'ema_kairi')
        df = __make_col_df(df, cls.ohlc.momentum, 'momentum')
        df = __make_col_df(df, cls.ohlc.rate_of_change, 'rate_of_change')
        df = __make_col_df(df, cls.ohlc.rsi, 'rsi')
        df = __make_col_df(df, cls.ohlc.williams_R, 'williams_R')
        df = __make_col_df(df, cls.ohlc.beta, 'beta')
        df = __make_col_df(df, cls.ohlc.tsf, 'tsf')
        df = __make_col_df(df, cls.ohlc.correl, 'correl')
        df = df.assign(normalized_ave_true_range=cls.ohlc.normalized_ave_true_range[cls.num_term:end])
        df = df.assign(three_outside_updown=cls.ohlc.three_outside_updown[cls.num_term:end])
        df = df.assign(breakway=cls.ohlc.breakway[cls.num_term:end])
        df = df.assign(dark_cloud_cover=cls.ohlc.dark_cloud_cover[cls.num_term:end])
        df = df.assign(dragonfly_doji=cls.ohlc.dragonfly_doji[cls.num_term:end])
        df = df.assign(updown_sidebyside_white_lines=cls.ohlc.updown_sidebyside_white_lines[cls.num_term:end])
        df = df.assign(haramisen=cls.ohlc.haramisen[cls.num_term:end])
        df = df.assign(hikkake_pattern=cls.ohlc.hikkake_pattern[cls.num_term:end])
        df = df.assign(neck_pattern=cls.ohlc.neck_pattern[cls.num_term:end])
        df = df.assign(upsidedownside_gap_three_method=cls.ohlc.upsidedownside_gap_three_method[cls.num_term:end])
        df = df.assign(future_side=cls.ohlc.future_side[cls.num_term:])
        print('future side unique val')
        print(df['future_side'].value_counts(dropna=False, normalize=True))
        return df

    @classmethod
    def generate_df_for_bot(cls):
        df = pd.DataFrame()
        df = df.assign(dt=cls.ohlc.dt[-1:])
        df = df.assign(open=cls.ohlc.open[-1:])
        df = df.assign(high=cls.ohlc.high[-1:])
        df = df.assign(low=cls.ohlc.low[-1:])
        df = df.assign(close=cls.ohlc.close[-1:])
        df = df.assign(size=cls.ohlc.size[-1:])
        def __make_col_df(df, data, col_name):
            for k in data:
                col = col_name + str(k)
                df = df.assign(col=data[k][-1:])
                df.rename(columns={'col': col}, inplace=True)
                return df
        df = __make_col_df(df, cls.ohlc.ema, 'ema')
        df = __make_col_df(df, cls.ohlc.ema_kairi, 'ema_kairi')
        df = __make_col_df(df, cls.ohlc.momentum, 'momentum')
        df = __make_col_df(df, cls.ohlc.rate_of_change, 'rate_of_change')
        df = __make_col_df(df, cls.ohlc.rsi, 'rsi')
        df = __make_col_df(df, cls.ohlc.williams_R, 'williams_R')
        df = __make_col_df(df, cls.ohlc.beta, 'beta')
        df = __make_col_df(df, cls.ohlc.tsf, 'tsf')
        df = __make_col_df(df, cls.ohlc.correl, 'correl')
        df = df.assign(normalized_ave_true_range=cls.ohlc.normalized_ave_true_range[-1:])
        df = df.assign(three_outside_updown=cls.ohlc.three_outside_updown[-1:])
        df = df.assign(breakway=cls.ohlc.breakway[-1:])
        df = df.assign(dark_cloud_cover=cls.ohlc.dark_cloud_cover[-1:])
        df = df.assign(dragonfly_doji=cls.ohlc.dragonfly_doji[-1:])
        df = df.assign(updown_sidebyside_white_lines=cls.ohlc.updown_sidebyside_white_lines[-1:])
        df = df.assign(haramisen=cls.ohlc.haramisen[-1:])
        df = df.assign(hikkake_pattern=cls.ohlc.hikkake_pattern[-1:])
        df = df.assign(neck_pattern=cls.ohlc.neck_pattern[-1:])
        df = df.assign(upsidedownside_gap_three_method=cls.ohlc.upsidedownside_gap_three_method[-1:])
        return df

    @classmethod
    @jit
    def calc_future_side(cls, future_side_period, future_side_kijun, ohlc):
        for i in range(len(ohlc.close) - future_side_period):
            buy_max = 0
            sell_max = 0
            for j in range(i, i + future_side_period):
                buy_max = max(buy_max, ohlc.high[j + 1] - ohlc.close[i])
                sell_max = max(sell_max, ohlc.close[i] - ohlc.low[j + 1])
            if buy_max >= future_side_kijun and sell_max >= future_side_kijun:
                ohlc.future_side.append('both')
            elif buy_max >= future_side_kijun and sell_max < future_side_kijun:
                ohlc.future_side.append('buy')
            elif buy_max < future_side_kijun and sell_max >= future_side_kijun:
                ohlc.future_side.append('sell')
            elif buy_max < future_side_kijun and sell_max < future_side_kijun:
                ohlc.future_side.append('no')
        return ohlc.future_side

    @classmethod
    @jit
    def __calc_ema(cls, term, close):
        return list(ta.EMA(np.array(close), timeperiod=term))

    @classmethod
    @jit
    def __calc_ema_kairi(cls, term, close):
        kairi = []
        ema = cls.__calc_ema(term, close)
        for i,em in enumerate(ema):
            if np.isnan(em):
                kairi.append(-1)
            else:
                kairi.append(100.0*(close[i] - em) / em)
        return kairi

    @classmethod
    @jit
    def __calc_momentum(cls, term, close):
        return list(ta.MOM(np.array(close), timeperiod=term))

    @classmethod
    @jit
    def __calc_rate_of_change(cls,term,close):
        return list(ta.ROC(np.array(close), timeperiod=term))

    @classmethod
    @jit
    def __calc_rsi(cls, term, close):
        return list(ta.RSI(np.array(close), timeperiod=term))

    @classmethod
    @jit
    def __calc_williams_R(cls, term, high, low, close):
        return list(ta.WILLR(np.array(high), np.array(low), np.array(close), timeperiod=term))

    @classmethod
    @jit
    def __calc_beta(cls, term, high, low):
        return list(ta.BETA(np.array(high), np.array(low), timeperiod=term))

    @classmethod
    @jit
    def __calc_time_series_forecast(cls, term, close):
        return list(ta.TSF(np.array(close), timeperiod=term))

    @classmethod
    @jit
    def __calc_correl(cls, term, high, low):
        return list(ta.CORREL(np.array(high), np.array(low), timeperiod=term))

    @classmethod
    @jit
    def __calc_normalized_ave_true_range(cls, high, low, close):
        return list(ta.NATR(np.array(high), np.array(low), np.array(close)))


    @classmethod
    @jit
    def __calc_three_outside_updown(cls, open, high, low, close):
        return list(ta.CDL3OUTSIDE(np.array(open), np.array(high), np.array(low), np.array(close)))

    @classmethod
    @jit
    def __calc_breakway(cls, open, high, low, close):
        return list(ta.CDLBREAKAWAY(np.array(open), np.array(high), np.array(low), np.array(close)))

    @classmethod
    @jit
    def __calc_dark_cloud_cover(cls, open, high, low, close):
        return list(ta.CDLDARKCLOUDCOVER(np.array(open), np.array(high), np.array(low), np.array(close),penetration=0))

    @classmethod
    @jit
    def __calc_dragonfly_doji(cls, open, high, low, close):
        return list(ta.CDLDRAGONFLYDOJI(np.array(open), np.array(high), np.array(low), np.array(close)))

    @classmethod
    @jit
    def __calc_updown_sidebyside_white_lines(cls, open, high, low, close):
        return list(ta.CDLGAPSIDESIDEWHITE(np.array(open), np.array(high), np.array(low), np.array(close)))

    @classmethod
    @jit
    def __calc_haramisen(cls, open, high, low, close):
        return list(ta.CDLHARAMI(np.array(open), np.array(high), np.array(low), np.array(close)))

    @classmethod
    @jit
    def __calc_hikkake_pattern(cls, open, high, low, close):
        return list(ta.CDLHIKKAKEMOD(np.array(open), np.array(high), np.array(low), np.array(close)))

    @classmethod
    @jit
    def __calc_neck_pattern(cls, open, high, low, close):
        return list(ta.CDLINNECK(np.array(open), np.array(high), np.array(low), np.array(close)))

    @classmethod
    @jit
    def __calc_upsidedownside_gap_three_method(cls, open, high, low, close):
        return list(ta.CDLXSIDEGAP3METHODS(np.array(open), np.array(high), np.array(low), np.array(close)))

    @classmethod
    @jit
    def generate_tick_pred_data(cls, ohlc, prediction): #assume index 0 of ohlc and prediction is matched
        tick = []
        pred = []
        split_num = 60
        for i in range(len(prediction)):
            om_tick = []
            if ohlc.open[i] < ohlc.close[i]:  # open, low, high, close
                ol = ohlc.open[i] - ohlc.low[i]
                lh = ohlc.high[i] - ohlc.low[i]
                hc = ohlc.high[i] - ohlc.close[i]
                sec_width = (ol + lh + hc) / split_num
                if sec_width > 0:
                    om_tick.extend(list(np.round(np.linspace(ohlc.open[i], ohlc.low[i], round(ol / sec_width)))))
                    om_tick.extend(list(np.round(np.linspace(ohlc.low[i], ohlc.high[i], round(lh / sec_width)))))
                    om_tick.extend(list(np.round(np.linspace(ohlc.high[i], ohlc.close[i], round(hc / sec_width)))))
                else:
                    om_tick.extend([tick[-1]] * 60)
            else:  # open, high, low, close
                oh = ohlc.high[i] - ohlc.open[i]
                hl = ohlc.high[i] - ohlc.low[i]
                lc = ohlc.close[i] - ohlc.low[i]
                sec_width = (oh + hl + lc) / split_num
                if sec_width > 0:
                    om_tick.extend(list(np.round(np.linspace(ohlc.open[i], ohlc.high[i], round(oh / sec_width)))))
                    om_tick.extend(list(np.round(np.linspace(ohlc.high[i], ohlc.low[i], round(hl / sec_width)))))
                    om_tick.extend(list(np.round(np.linspace(ohlc.low[i], ohlc.close[i], round(lc / sec_width)))))
                else:
                    om_tick.extend([tick[-1]] * 60)
            if 60 - len(om_tick) > 0:
                om_tick.extend([om_tick[-1] * (60 - len(om_tick))])
            elif 60 - len(om_tick) < 0:
                del om_tick[-(len(om_tick) - 60):]
            tick.extend(om_tick)
            pred.extend([prediction[i]] * 60)
        return (tick, pred)