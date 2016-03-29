import json
import os

from cStringIO import StringIO
from netaddr import IPAddress, IPNetwork

from utils import execute

TIMEOUT = 5

def ovs_vsctl(args):
    full_args = ['ovs-vsctl', '--timeout=%s' % TIMEOUT] + args
    execute(*full_args)

def create_ovs_port(bridge, dev):
    ovs_vsctl(['--', '--if-exists', 'del-port', dev, '--',
               'add-port', bridge, dev])

def delete_ovs_port(bridge, dev):
    ovs_vsctl(['--', '--if-exists', 'del-port', bridge, dev])
    delete_net_dev(dev)

def gateway_get(network):
    result, _ = execute('docker', 'network', 'inspect', network)
    nets = json.load(StringIO(result))
    config = nets[0]['IPAM']['Config'][0]

    if not config.get('Gateway'):
        gateway = str(IPAddress(IPNetwork(config['Subnet']).first + 1))
    else:
        gateway = config['Gateway']

    return gateway

def device_exists(dev):
    """Check if ethernet device exists."""
    return os.path.exists('/sys/class/net/%s' % dev)

def delete_net_dev(dev):
    """Delete a network device only if it exists."""
    if device_exists(dev):
        execute('ip', 'link', 'delete', dev)

def set_mac(dev, address):
    execute('ip', 'link', 'set', dev, 'address', address)

def set_addr(dev, address):
    broadcast = str(IPNetwork(address).broadcast)
    execute('ip', 'addr', 'replace', address, 'broadcast', broadcast, 'dev', dev)

def plugin(if_local_name, if_remote_name):
    execute('ip', 'link', 'add', if_local_name, 'type',
            'veth', 'peer', 'name', if_remote_name)
    execute('ip', 'link', 'set', if_local_name, 'up')
