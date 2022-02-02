#!/usr/bin/env python3
from saomsg.msgtoindi import msg_device
from saomsg.msgtoindi import wrapper as MSG
#from saomsg.msgtoindi import wrapper as MSG
import os
import asyncio
import logging
logging.getLogger().setLevel(logging.DEBUG)




class TEMPBINO(msg_device):



    @MSG.subscribe('TEMPBINO', 'log')
    def log(self, item, value):
        self.IDMessage(f"NEW LOG VALUE {value}")



async def main():
    m = TEMPBINO("tempbino-tunnel", 2523, "TEMPBINO")
    await m.astart()

asyncio.run(main())





