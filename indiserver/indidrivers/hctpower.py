#!/usr/bin/env python3
from saomsg.msgtoindi import msg_device
from saomsg.msgtoindi import wrapper as MSG
#from saomsg.msgtoindi import wrapper as MSG
import os
import asyncio
import logging
logging.getLogger().setLevel(logging.DEBUG)




class HCTPOWER(msg_device):
    pass



async def main():
    m = HCTPOWER("clark", 6111, "HCTPOWER")
    await m.astart()

asyncio.run(main())





