import requests
import pandas as pd
import os
from datetime import datetime
from datetime import timedelta
from OneMinutesData import OneMinutesData

class CryptowatchDataGetter:
    @classmethod
    def check_csv_data(cls):
        df = pd.read_csv('one_min_data.csv')
        dt = df['dt']
        ut = df['unix_time']
        return dt[len(dt)-1], ut[len(ut)-1]

    @classmethod
    def get_data_from_crptowatch(cls, before='', after=''):
        url = 'https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc'
        query = {
            'periods': 60,
            'before': before,
            'after': after,
        }
        res = requests.get(url, params = query).json()['result']['60']
        return res

    @classmethod
    def convert_json_to_ohlc(cls, json_data):
        omd = OneMinutesData()
        omd.initialize()
        for data in json_data:
            omd.unix_time.append(data[0])
            omd.dt.append(datetime.fromtimestamp(data[0]))
            omd.open.append(data[1])
            omd.high.append(data[2])
            omd.low.append(data[3])
            omd.close.append(data[4])
            omd.size.append(data[5])
        return omd

    @classmethod
    def write_data_to_csv(cls, one_min_data: OneMinutesData):
        df = pd.DataFrame()
        df = df.assign(unix_time=one_min_data.unix_time)
        df = df.assign(dt=one_min_data.dt)
        df = df.assign(open=one_min_data.open)
        df = df.assign(high=one_min_data.high)
        df = df.assign(low=one_min_data.low)
        df = df.assign(close=one_min_data.close)
        df = df.assign(size=one_min_data.size)
        df.to_csv('one_min_data.csv',index=False)

    @classmethod
    def read_csv_data(cls):
        df = pd.read_csv('one_min_data.csv')
        return df

    @classmethod
    def get_and_add_to_csv(cls):
        if os.path.exists('one_min_data.csv'):
            dt, unix_dt = cls.check_csv_data()
            df_ori = cls.read_csv_data()
            json_data = cls.get_data_from_crptowatch(after=unix_dt)
            omd = cls.convert_json_to_ohlc(json_data)
            from_ind = 0
            for i in range(len(omd.unix_time)):
                if omd.unix_time[i] == unix_dt:
                    from_ind = i+1
                    break
            df = pd.DataFrame()
            df = df.assign(unix_time = omd.unix_time[from_ind:])
            df = df.assign(dt=omd.dt[from_ind:])
            df = df.assign(open=omd.open[from_ind:])
            df = df.assign(high=omd.high[from_ind:])
            df = df.assign(low=omd.low[from_ind:])
            df = df.assign(close=omd.close[from_ind:])
            df = df.assign(size=omd.size[from_ind:])
            df_ori = pd.concat([df_ori, df], ignore_index=True, axis=0)
            df_ori.to_csv('one_min_data.csv',index=False)
        else:
            dt = datetime.now()+timedelta(minutes=-6001)
            res = cls.get_data_from_crptowatch(after=int(dt.timestamp()))
            omd = cls.convert_json_to_ohlc(res)
            cls.write_data_to_csv(omd)




if __name__ == '__main__':
    CryptowatchDataGetter.get_data_from_crptowatch()