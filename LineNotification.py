import requests
from LogMaster import LogMaster
from SystemFlg import SystemFlg
import asyncio
import threading
from datetime import datetime


class LineNotification:
    @classmethod
    def initialize(cls):
        cls.__read_keys()
        cls.last_error = ''
        print('initialized LineNotification')

    @classmethod
    def __read_keys(cls):
        file = open('./ignore/line.txt', 'r')  # 読み込みモードでオープン
        cls.token = file.readline().split(':')[1]
        file.close()

    @classmethod
    def send_notification(cls):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cls.__send_performance_data())
        #loop.run_until_complete(cls.__send_position_and_order_data())

    @classmethod
    def send_message(cls, message):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cls.__send_message2(message))

    @classmethod
    async def __send_message2(cls, message):
        if len(message) > 0:
            await cls.__send_message('\r\n'+str(message))


    @classmethod
    async def __send_performance_data(cls):
        p = LogMaster.get_latest_performance()
        if len(p) > 0:
            await cls.__send_message('\r\n'+'['+str(p['log_dt'].strftime("%m/%d %H:%M:%S"))+']'+
                             '\r\n'+'pl='+str(p['pl'])+
                            '\r\n' + 'pl_per_min=' + str(p['pl_per_min']) +
                             '\r\n'+'num_trade='+str(p['num_trade'])+
                             '\r\n'+'win_rate='+str(p['win_rate']))

    @classmethod
    async def __send_position_and_order_data(cls):
        p = LogMaster.get_latest_position()
        if len(p) > 0:
            await cls.__send_message('\r\n' + 'posi_side=' + p['posi_side'] + ', posi_price=' + str(p['posi_price']) +', posi_size=' + str(p['posi_size']))

    @classmethod
    async def get_latest_api_error(cls):
        p = LogMaster.get_latest_api_error()
        if len(p) > 0:
            if p['api_error'] != cls.last_error:
                cls.last_error = p['api_error']
                cls.send_message('\r\n' + 'API Error Occured!' + '\r\n' + p['api_error'])

    @classmethod
    async def __send_message(cls, message):
        url2 = "https://notify-api.line.me/api/notify"
        headers = {"Authorization": "Bearer " + cls.token}
        payload = {"message": message}
        try:
            res = requests.post(url2, headers=headers, data=payload, timeout=(6.0))
        except Exception as e:
            print('Line notify error!={}'.format(e))




if __name__ == '__main__':
    LineNotification.initialize()
    LineNotification.send_message('\r\n'+'pl=-59'+'\r\n'+'num_trade=100')

