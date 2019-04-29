import pandas as pd
import mpl_finance as mpf
from collections import OrderedDict
import matplotlib
import matplotlib.pyplot as plt
from MarketData2 import MarketData2

class Chart:
    def display_result(self, from_ind, to_ind, results):
        df_ohlcv = MarketData2.ohlc_bot.dt[from_ind:to_ind].set_index('date')

        # 移動平均（SMA：Simple Moving Average）の算出（期間10）
        df_sma = pd.DataFrame(OrderedDict({'SMA10':  df_ohlcv['close'].rolling(10).mean(),}))

        # 描画領域を作成
        fig = plt.figure(figsize=(20,20))
        ax = plt.subplot(1,1,1)

        # チャート表示数にDataFrameをトリミング
        df_ohlcv = df_ohlcv.iloc[-121:]
        df_sma   = df_sma.iloc[-121:]

        # ロウソクチャートをプロット
        mpf.candlestick2_ohlc(ax,
                              opens     = df_ohlcv["open"],
                              highs     = df_ohlcv["high"],
                              lows      = df_ohlcv["low"],
                              closes    = df_ohlcv["close"],
                              width     = 0.8,
                              colorup   = "#46AE74",
                              colordown = "#E4354A")

        # x軸をdateにする
        xdate = df_ohlcv.index
        x_int_list = range(0, len(xdate), 6)
        ax.set_xticks(x_int_list)
        ax.set_xticklabels((xdate[int(x)].strftime('%d %H:%M') for x in x_int_list))

        # グラフの両サイドをトリム
        ax.set_xlim([-1, 121])

        # 移動平均（SMA：Simple Moving Average）をプロット
        df_sma.reset_index(inplace=True)
        ax.plot(df_sma['SMA10'], color='Blue', linewidth='1.0', label='SMA10')

        # x軸の整形
        fig.autofmt_xdate(bottom=0.2, rotation=30, ha='right')

        # グラフの描画
        plt.show()