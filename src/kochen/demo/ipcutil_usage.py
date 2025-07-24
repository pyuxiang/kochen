# Server-side
from kochen.ipcutil import Server
from physicsutils.devices.powermeter import Powermeter

pm = Powermeter()
s = Server()
s.register(pm)
s.run()


# Client-side
from kochen.ipcutil import Client

pm = Client()
pm.help("get_voltage")
print(pm.get_voltage())
