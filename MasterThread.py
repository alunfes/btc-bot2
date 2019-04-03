import time
import asyncio
from SystemFlg import SystemFlg
from WebsocketMaster import WebsocketMaster
from MarketData import  MarketData


class MasterThread:
    SystemFlg.initialize()
    ws = WebsocketMaster('lightning_executions_','FX_BTC_JPY')
    time.sleep(5)
    MarketData.initialize_and_start(110)


    loop = asyncio.get_event_loop()
    asyncio.ensure_future(ws.loop())
    loop.run_forever()

