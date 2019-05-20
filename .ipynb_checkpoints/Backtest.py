from backtesting import Strategy
from backtesting import Backtest



class OriginalBacktest(Strategy):
    n1 = 10
    n2 = 20

    def init(self):


    def next(self):
        if self.data['']
            self.buy()

        elif crossover(self.sma2, self.sma1):
            self.sell()

if __name__ == '__main__':
    bt = Backtest(GOOG, OriginalBacktest, cash=10000, commission=0)
    bt.run()
