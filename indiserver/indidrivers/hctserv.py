#!/usr/bin/env python3
from saomsg.msgtoindi import msg_device
from saomsg.msgtoindi import wrapper as MSG
import os
import asyncio
import logging
logging.getLogger().setLevel(logging.DEBUG)



class HCTSERV(msg_device):
    pass


async def main():
    #m = HCTSERV("hardware-tunnel", 2345, "HCTSERV")
    m = HCTSERV("ops2.mmto.arizona.edu", 6667, "HCTSERV")
    await m.astart()

asyncio.run(main())





