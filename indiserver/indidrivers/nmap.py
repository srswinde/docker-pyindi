#!/usr/bin/env python
from pyindi.device import device
import asyncio
import os
from xml.etree import ElementTree as etree
import re
from pathlib import Path
import logging
import re
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select 
from sqlalchemy.schema import MetaData
import traceback
from mmt_inst.remote import connect_ssh
import traceback
import json

class NMAPResponse:

    def __init__(self, xmlstr, services):
        self.xmlstr = xmlstr
        self.xml = etree.fromstring(xmlstr)
        tagnames = [tag.tag for tag in self.xml]
        tags = ['scaninfo', 
                'verbose',
                'debugging',
                'runstats'
                ]
        self.services = services
        for tag in tags:
            if tag not in tagnames:
                raise RuntimeError(f"Missing tag {tag} from xml.")

    def isup(self):
            return self.xml[-1][1].attrib['up'] == '1'

    def ports(self):
        if not self.isup():
            return {}
        
        resp = {}
        hostele = self.xml.find("host")
        portsele = hostele.find("ports")
        for port in portsele:
            if port.tag != "port":
                continue


            num = port.attrib['portid']
            resp[num] = {
                    "open": port[0].attrib['state'] == "open",
                    "reason": port[0].attrib['reason'],
                    "service":[]
                    }
            logging.debug(f"{port.attrib['portid']} {port[0].attrib['state']}")
            if self.services:
                pservices = self.services[self.services.port == int(num)]
                for idx, srv in pservices.iterrows():
                    logging.debug(srv)
                    resp[num]['service'].append(srv.server)

        return resp

class database:

    def __init__(self, uri=None):
        if uri is None:
            host = os.environ["DB_HOST"]
            password = os.environ["POSTGRES_PASSWORD"]
            user = os.environ["POSTGRES_USER"]
            db = os.environ["POSTGRES_DB"]

            uri = f"postgresql+asyncpg://{user}:{password}@{host}/{db}"

        self.engine = create_async_engine( uri )

    def begin(self):
        return self.engine.begin()

    def connect(self):
        return self.engine.connect()

    def session(self, expire_on_commit=True):
        async_session = AsyncSession(
                self.engine,
                expire_on_commit=expire_on_commit,
                )

        return async_session
    
    async def get_services(self):
        """Gather the msg_hosts and msg_services from the database.
        organize them such that we have 
        {
            <host1>: [
                {<port1>:
                    [<SERVIC_NAME1>, <SERVICE_NAME2>...]
                }
                ...
            ],
            ...
        }
        """
        
        async with self.engine.connect() as conn:
            metadata = MetaData()
            await conn.run_sync(metadata.reflect)

            msg_hosts = metadata.tables['msg_hosts']
            msg_services = metadata.tables['msg_services']

            result = await conn.execute(select(msg_services))
            service_recs = result.fetchall()

            result = await conn.execute(select(msg_hosts))
            host_recs = result.fetchall()
            data = {}
            network = {}

            for _, name, on_mmt_network in host_recs:
                network[name] = on_mmt_network

            for _, name, host, port in service_recs:
                if host in data:
                    if port in data[host]['services']:
                        data[host]['services'][port].append(name)
                    else:
                        data[host]['services'][port] = [name]

                else:
                    if host in network:
                        
                        data[host] = dict(
                            services = {port:[name]},
                            mmt_network = network[host]
                            )

            return data

    async def get_hosts(self):
        
        async with self.session() as dbsession:
            result = await dbsession.execute(select(msg_hosts))
            recs = []
            for rec in result.all():
                recs.append({
                    "hostname":rec[0].hostname,
                    "on_mmt_network":rec[0].on_mmt_network
                    })
            
        return pd.DataFrame(recs)


class nmap(device):
    """INDI Driver class"""
    servers = None
    test = False
    def ISGetProperties(self, device=None):

        if self.servers is None:
            self.servers = []
        
        

    def initProperties(self):
        # Add Hacksaw its not in the database.

        vec = self.vectorFactory(
                "Switch",
                dict(
                    device=self.device,
                    name="dummy",
                    label="dummy",
                    perm='rw',
                    state="Idle", 
                    rule="OneOfMany",
                    group="dummy"
                    ),
                [
                    dict(
                        name="dummy",
                        state="Off"
                        )
                    ]

                )

        self.IDDef(vec)

    @device.NewVectorProperty('dummy')
    def dummy(self, *args):
        self.ssh_bridge_que.put_nowait("FOOBAR")

    async def asyncInitProperties(self, device=None):
#        db = database()
#        services = await db.get_services()
#        for name, info in services.items():
#            if True: #if info['mmt_network']:
#                services = info['services']
#                ports_with_first_name = {port:names[0] for port,names in services.items()}
#                self.buildServerGroup(name, f"{name}.mmto.arizona.edu", ports_with_first_name)
        try:
            msg_path = os.environ.get("MSG_SERVER_DIR")
            if msg_path is None:
                raise RuntimeError(f"MSG_SERVER_DIR env variable is not defined.")

            msg_path=Path(msg_path)
            regex = re.compile("(?P<host>[a-z]+)-env.json")
            jfiles = {}
            for fpath in msg_path.iterdir():
                self.IDMessage(f"File path is {str(fpath)}")
                match = regex.match(fpath.name)
                if match:
                    jfiles[match.groupdict()['host']] = fpath

            for host,fpath in jfiles.items():
                self.IDMessage(host)
                with fpath.open() as fd:
                    jdata = json.load(fd)

                portlist = {}
                for name, info in jdata.items():
                    formated_info = dict(
                        name=name,
                        aliases=info['aliases'],
                        description=info['description'],
                        links=info['links']
                    )
                    portlist[info['port']] = formated_info
                
                self.buildServerGroup(host, f"{host}.mmto.arizona.edu", portlist)

        except Exception as error:
            self.IDMessage(str(error))
            self.IDMessage(traceback.format_exc())



    def buildServerGroup(self, label, servername, portlist):
        f"""
            Create widgets based on the server name and 
            assoicated services/ports. 
        """
        self.servers.append(label)

        button_att = dict(
            device=self.device,
            name=f"scan_{label}",
            label=label, 
            perm="rw",
            state="Idle",
            group=label,
            rule="AtMostOne"
        )

        buttons = [
                dict(
                    name="scan",
                    label="Scan",
                    state="off"
                    ),
                dict(
                    name="repeat",
                    label="Continuous Scan",
                    state="off"
                    ), 
                dict(
                    name="stop",
                    label="Stop",
                    state="On"
                    ),

                ]

        vec = self.vectorFactory(
                "Switch",
                button_att,
                buttons
                )
        self.IDDef(vec)
        self.IDSet(
            self.IUFind(
                vec.name
                )
            )

        light_att = dict(
                device=self.device,
                name=f"ports_{label}",
                state="Idle",
                label="Ports",
                group=label
                )

        lights = []
        for port, info in portlist.items():
            name = info['name']
            lights.append(
                    dict(
                        name=str(port),
                        label=f"{name} ({str(port)})",
                        state='Idle'
                        )
                    )

        vec = self.vectorFactory(
                "Light",
                light_att,
                lights
                )
        self.IDDef(vec)
        self.IDSet(
            self.IUFind(
                vec.name
                )
            )


        number_att = dict(
                device=self.device,
                name=f"last_scan_{label}",
                label="Last Scan",
                state="Idle",
                group=label,
                perm="ro"
                )
        numbers = [
                dict(
                    name="timestamp",
                    label="Timestamp",
                    format="%d",
                    min=0,
                    max=1e10,
                    step=1,
                    value=0
                    )
                ]
        vec = self.vectorFactory(
                "Number",
                number_att,
                numbers
                )
        self.IDDef(vec)
        self.IDSet( self.IUFind( vec.name ) )

        text_att = dict(
                device=self.device,
                name=f"last_scan_str_{label}",
                label="Last Scan",
                state="Idle",
                group=label,
                perm='ro'
                )
        texts = [
                dict(
                    name="timestamp",
                    label="Timestamp",
                    text=""
                    )
                ]
        

        vec = self.vectorFactory(
                "Text",
                text_att,
                texts
                )
        self.IDDef(vec)
        self.IDSet(self.IUFind(vec.name))


        
    def ISNewSwitch(self, device, name, values, names):
        """
        Here we handle all the Scan switches. 
        """
        regex = re.compile(r"scan_([a-zA-z_]*)")
        match = regex.match(name)

        if name == "dummy":
            self.IDMessage("FUCK YOU")

        #dict of new values
        vdict = dict(zip(names, values))
        if match:
            vec = self.IUFind(name)
            if 'stop' in vdict:
                vec['repeat'] = 'Off'

            elif 'repeat' in vdict:
                vec['stop'] = 'Off'

            if 'scan' in vdict:
                if vec['scan'].value == "On":
                    # We are in the middle of a
                    # one time scan. So don't 
                    # do anything.
                    return 
            
            self.IDMessage(name)
            vec = self.IUUpdate(device, name, values, names)
            self.IDSet(vec)
            self.IDMessage(self.nmap_queue)
            self.nmap_queue.put_nowait(
                    match.group((1))
                    )

    async def nmap_async_bridge(self):
        """Wait for an nmap request from the nmap_queue.
        We use a queue so only one scan is done at a time.
        We don't want to flood the network with port sniffing. 
        """

        self.nmap_queue = asyncio.Queue()
        while True:
            server = await self.nmap_queue.get()
            button_set = self.IUFind(f"scan_{server}")
            port_lights = self.IUFind(f"ports_{server}")
            last_scan = self.IUFind(f"last_scan_{server}")
            last_scan_str = self.IUFind(f"last_scan_str_{server}")
            button_set.state = "Busy"
            self.IDSet(button_set)
            servername = port_lights.group
            
            ports = [prop.name for prop in port_lights]
            self.IDMessage(ports) 


            try: 
                async with connect_ssh('fields.mmto.arizona.edu', 'swindell') as ssh:
                    scan = await ssh.nmap(servername, ports)
                    scan = NMAPResponse(scan.stdout, services=None)
                #scan = await self.easy_nmap(servername, ports)
            except Exception as error:
                self.IDMessage(f"scan problem {error}")
                continue
    
            if type(scan) == bytes:
                self.IDMessage(f"Scan error {scan.decode()}")
                await asyncio.sleep(0.5)
                continue

            if scan.isup():
                button_set.state="Ok"
            else:
                button_set.state="Alert"
            button_set["scan"].value = "Off"

            for portno, status in scan.ports().items():

                if status['open']:
                    port_lights[str(portno)].value = "Ok"
                else:
                    port_lights[str(portno)].value = "Alert"

            now = time.time()
            last_scan['timestamp'].value = int(now)
            last_scan_str['timestamp'].value = time.ctime(now)


            self.IDSet(button_set)
            self.IDSet(port_lights)
            self.IDSet(last_scan)
            self.IDSet(last_scan_str)
                        
            




    @device.repeat(5000)
    async def idle(self):
        """Handle the continuous scan."""

        for server in self.servers:
            last_scan = self.IUFind(f"last_scan_{server}")
            button_set = self.IUFind(f"scan_{server}")
            now = time.time()
            
            if button_set['repeat'].value == "On":
                if (now - last_scan['timestamp'].value) > 60:
                    self.nmap_queue.put_nowait(server)






    async def easy_nmap(self, host, ports=[], services=None):
        """Create a subprocess with the nmap cmd. 
        Try to wrap the response in a NMAPResponse 
        class. 
        """
        self.IDMessage(f"ports = {ports}")
        portlist = [str(port) for port in ports]
        if len(portlist) == 0:
            cmd = f"nmap -vvv -oX - {host}"
        else:
            cmd = f"nmap -vvv -p {','.join(portlist)} -oX - {host}"

        self.IDMessage(f"easy_nmap cmd -> {cmd}")
        proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

        self.IDMessage(f"easy_nmap proc-> {proc}")
        stdout, stderr = await proc.communicate()

        if proc.returncode > 0:
            if b"Your port specifications are illegal" in stderr:
                self.IDMessage("port error")
                self.IDMessage(','.join(portlist))
            else:
                self.IDMessage(f"Error {stderr.decode()}")
            return stdout
        else:
            try:

                return NMAPResponse(stdout.decode(), services)
            except Exception as error:
                self.IDMessage(traceback.format_exc())




async def main():
    device = nmap()
    await device.astart(
            device.nmap_async_bridge(),
            )

asyncio.run(main())
