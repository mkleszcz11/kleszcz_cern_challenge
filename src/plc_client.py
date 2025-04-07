from asyncua import Client
import asyncio


class PLCClient:

    def __init__(self, url, timeout):
        #: OPC UA client
        self.client = Client(url, timeout)


    async def set_object_value(self, name, value):
        myvar = await self.myobj.get_child(f"{self.idx}:{name}")
        await myvar.write_value(value)

    async def get_object_value(self, name):
        myvar = await self.myobj.get_child(f"{self.idx}:{name}")
        value = await myvar.read_value()
        return value

    async def get_alarm_status(self, name):
        myalarm = await self.myobj.get_child(f"{self.idx}:{name}")
        myvar = await myalarm.get_child(f"{self.idx}:Status")
        value = await myvar.read_value()
        return value
    
    async def set_object_pulse(self, name):
        myvar = await self.myobj.get_child(f"{self.idx}:{name}")
        await myvar.write_value(True)
        await asyncio.sleep(0.5)
        await myvar.write_value(False)
        
    async def disconnect(self):
        await self.client.disconnect()

    async def init(self):
        await self.client.connect()
        namespace = "http://examples.freeopcua.github.io"
        self.idx = await self.client.get_namespace_index(namespace)
        print("nsidx", self.idx)
        self.myobj = await self.client.nodes.root.get_child(
            ["0:Objects", f"{self.idx}:myPLC"]
        )
