'''

'''

import catboost as cb
from catboost import Pool
from numba import jit
import pickle
import numpy as np
import pandas as pd


class CatModel:
    @jit
    def generate_data(self, df: pd.DataFrame, test_size=0.2):
        df['future_side'] = df['future_side'].map({'no': 0, 'buy': 1, 'sell': 2, 'both': 3}).astype(int)
        df = df.drop(['dt', 'open', 'high', 'low', 'close', 'size'], axis=1)
        size = int(round(df['future_side'].count() * (1 - test_size)))
        train_x = df.drop('future_side', axis=1).iloc[0:size]
        train_y = df['future_side'].iloc[0:size]
        test_x = df.drop('future_side', axis=1).iloc[size:]
        test_y = df['future_side'].iloc[size:]
        return train_x, test_x, train_y, test_y

    @jit
    def generate_bot_pred_data(self, df:pd.DataFrame):
        if 'future_side' in df.columns:
            return df.drop(['dt', 'open', 'high', 'low', 'close', 'size', 'future_side'], axis=1)
        else:
            return df.drop(['dt', 'open', 'high', 'low', 'close', 'size'], axis=1)


    def read_dump_model(self, path):
        with open(path, mode='rb') as f:
            return pickle.load(f)

    @jit
    def train(self, train_x, train_y):
        train_pool = Pool(train_x, label=train_y)
        params = {
            'loss_function': 'MultiClass',
            'num_boost_round': 10000,
            'early_stopping_rounds': 10,
            'task_type': 'GPU',
        }
        model = cb.CatBoostClassifier(loss_function="MultiClass",
                                   num_boost_round=10000,
                                   task_type='GPU',
                                   verbose=1000,
                                   )
        model.fit(train_pool)
        return model

    @jit
    def calc_accuracy(self, predict, test_y):
        num = len(predict)
        matched = 0
        y = np.array(test_y)
        for i in range(len(predict)):
            if predict[i] == y[i]:
                matched += 1
        return float(matched) / float(num)
