import xgboost as xgb
import numpy as np
import pandas as pd
import pickle
from numba import jit

class XgbModel:
    @jit
    def generate_data(self, df:pd.DataFrame, test_size=0.2):
        df['future_side'] = df['future_side'].map({'no':0, 'buy':1, 'sell':2, 'both':3}).astype(int)
        df = df.drop(['dt','open','high','low','close','size'],axis = 1)
        size = int(round(df['future_side'].count() * (1-test_size)))
        if test_size >=1:
            size = df.shape[0]
        train_x = df.drop('future_side',axis=1).iloc[0:size]
        train_y = df['future_side'].iloc[0:size]
        test_x = df.drop('future_side',axis=1).iloc[size:]
        test_y = df['future_side'].iloc[size:]
        return train_x, test_x, train_y, test_y

    @jit
    def generate_bot_pred_data(self, df:pd.DataFrame):
        if 'future_side' in df.columns:
            return df.drop(['dt', 'open', 'high', 'low', 'close', 'size', 'future_side'], axis=1)
        else:
            return df.drop(['dt', 'open', 'high', 'low', 'close', 'size'], axis=1)

    @jit
    def read_dump_model(self, path):
        with open(path, mode='rb') as f:
            return pickle.load(f)

    '''
    'n_round': 873, 
    'booster': 'gbtree', 
    'max_depth': 2, 
    'eta': 0.014665358030762696, 
    'gamma': 0.06164324304230239, 
    'grow_policy': 'lossguide', 
    'min_child_weight': 16, 
    'subsample': 0.5, 
    'colsample_bytree': 0.3578383397468333, 
    'colsample_bylevel': 0.8375960956222188, 
    'colsample_bynode': 0.5890703429135455, 
    'alpha': 0.025096283242450567, 
    'lambda': 1.2353050553508833e-06}.
    '''
    @jit
    def train(self, train_x, train_y):
        print('train_x', train_x.shape)
        print('train_y', train_y.shape)
        train = xgb.DMatrix(train_x, label = train_y)
        param = {
            'max_depth': 4,
            'num_class': 4,
            #'booster': 'gbtree',
            'eta': 0.005,
            'gamma': 1,
            #'grow_policy': 'lossguide',
            'min_child_weight': 1,
            'subsample': 0.9,
            'colsample_bytree': 0.9,
            #'colsample_bylevel': 0.8375960956222188,
            #'colsample_bynode': 0.5890703429135455,
            #'alpha': 0.025096283242450567,
            'lambda': 3,
            'objective': 'multi:softmax',
            'silent': True}
        num_round = 10000
        bst = xgb.train(param, train, num_round)
        return bst

    @jit
    def calc_accuracy(self, predict, test_y):
        num = len(predict)
        matched = 0
        y = np.array(test_y)
        for i in range(len(predict)):
            if predict[i] == y[i]:
                matched += 1
        return float(matched) / float(num)

    @jit
    def calc_specific_accuracy(self, predict, test_y, target_future_id):
        num = pd.Series(test_y).value_counts()[target_future_id]
        matched = 0
        y = np.array(test_y)
        for i in range(len(predict)):
            if y[i] == target_future_id and predict[i] == target_future_id:
                matched += 1
        return float(matched) / float(num)


if __name__ == '__main__':
    from CryptowatchDataGetter import  CryptowatchDataGetter
    from MarketData2 import  MarketData2

    print('downloading data.')
    CryptowatchDataGetter.get_and_add_to_csv()
    print('generating data.')
    MarketData2.initialize_from_bot_csv(100, 1, 215, 1600)
    train_df = MarketData2.generate_df(MarketData2.ohlc_bot)
    model = XgbModel()
    print('transforming data.')
    train_x, test_x, train_y, test_y = model.generate_data(train_df, 0.0)
    data = pd.concat([train_y, train_x], axis=1)
    data.to_csv('./Model/train_data.csv',header=False,index=False)
    print('generated xgb training data.')