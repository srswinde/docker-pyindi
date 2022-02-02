#!/usr/bin/python3
from pyindi.device import device
import asyncio


class Dummy(device):

    def ISGetProperties(self, device=None):
        pass

    async def initProperties(self):
        vec = self.vectorFactory('text',
                dict(
                    device=self.device,
                    name="text",
                    label="text",
                    state='Idle',
                    perm='rw',
                    group='MAIN'
                    )
                [
                    dict(
                        name='text',
                        label='text',
                        text='init'
                        )
                    ]
                )
        self.IDDef(vec)
    

    @device.NewVectorProperty('text')
    def handleText(self, device, name, values, names):
        vec = self.IUFind(name)
        self.IDMessage(f"Old value {vec[0].value}")
        self.IDMessage(f"New value {values[0]}")

    @device.repeat(5000)
    async def repeater(self):
        self.IDMessage("This message will repeat every 5000ms.")

async def main():
    d=Dummy()
    await d.astart()

asyncio.run(main())
