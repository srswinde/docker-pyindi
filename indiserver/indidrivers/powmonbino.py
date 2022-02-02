#!/usr/bin/env python3
from saomsg.msgtoindi import msg_device
from saomsg.msgtoindi import wrapper as MSG
import os
import asyncio
import logging
import requests

logging.getLogger().setLevel(logging.DEBUG)



class POWMONBINO(msg_device):
    last_state=None
    
    async def buildProperties(self):

        await super().buildProperties()

        vec = self.vectorFactory(
                "Text",
                dict(
                       device=self.device,
                       name="BINOSTATE",
                       perm='ro',
                       label="state",
                       group="Quick Look",
                       state="Idle"
                    ),
                [
                    dict(
                        name='state',
                        label="State",
                        text="None"
                        )
                    ]
                )
        self.IDDef(vec)
        self.IDSet(vec)

    @MSG.subscribe("POWMONBINO", 'state')
    def handle_state(self, item, value):
        if self.last_state != value[0]:
            if self.last_state is not None:
                msg = f"Alert powmonbino changed from {self.last_state} to {value[0]}"
                self.IDMessage(msg)
                self.email("BINO State Change", msg)
        vec = self.IUFind('BINOSTATE')
        vec['state'].value = value[0]
        self.IDSet(vec)
        self.last_state = value[0]



    def email(self, subject, msg):
        url = "https://ops.mmto.arizona.edu/mmt-notify/api/email"

        payload = {
          "to":["sswindell@mmto.org"],
          "subject":subject,
          "msg":msg,
          "trysms":True
        }
        rq=requests.get(url, data=payload)
        self.IDMessage(rq.content.decode())


async def main():
    m = POWMONBINO("bird-tunnel", 2537, 'POWMONBINO')
    await m.astart()

asyncio.run(main())





