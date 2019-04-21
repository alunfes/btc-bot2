import csv
import os
import asyncio


class LogMaster:
    @classmethod
    def initialize(cls):
        cls.log_file = './bot_log.csv'
        if os.path.isfile(cls.log_file):
            os.remove('./bot_log.csv')
        cls.ind_updates = 0 #current index wrote to csv file
        cls.index = 0
        cls.key_list = ['index','dt', 'open','high','low','close','posi_side', 'posi_price', 'posi_size', 'order_side',
                        'order_price', 'order_size', 'num_private_access', 'num_public_access', 'num_private_per_min',
                        'pl', 'num_trade', 'win_rate', 'prediction', 'api_error', 'action_message']
        cls.log_list = []

    @classmethod
    def add_log(cls, dict_log):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cls.__add_log(dict_log))

    @classmethod
    async def __add_log(cls, dict_log):
        if len(dict_log.keys()) > 0:
            d = {}
            d['index'] = cls.index
            cls.index += 1
            for key in dict_log.keys():
                for kl in cls.key_list:
                    if key == kl:
                        d[key] = dict_log[key]
            cls.log_list.append(d)
        if cls.ind_updates == 0:
            await cls.__all_log_to_csv()
        else:
            await cls.__add_log_to_csv()

    @classmethod
    async def __all_log_to_csv(cls):
        try:
            with open(cls.log_file, 'w') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=cls.key_list)
                writer.writeheader()
                for data in cls.log_list:
                    writer.writerow(data)
                    cls.ind_updates += 1
        except IOError as e:
            print('IO error!'+str(e))

    @classmethod
    async def __add_log_to_csv(cls):
        try:
            with open(cls.log_file, 'a') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=cls.key_list)
                log_data = cls.log_list[cls.ind_updates:]
                for data in log_data:
                    writer.writerow(data)
                    cls.ind_updates += 1
        except IOError as e:
            print('IO error!' + str(e))









