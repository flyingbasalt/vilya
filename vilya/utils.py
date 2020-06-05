import os
import math
import pathlib
import glob
import json
import urllib.request
import http.client
import hashlib
import functools
import socket
import time
import psutil
import tomlkit
from subprocess import run, Popen, PIPE


NA = 'n/a'

NTP_FIELDS = ['refid',  # see http://support.ntp.org/bin/view/Support/RefidFormat
              '_',
              'stratum',
              'ref_t',
              'sys_t',
              'last_offset',
              'rms_offset',
              '_', '_', '_',
              'root_delay',
              'root_disp',
              'update_int',
              'leap_status', 
              ]


def lcm(a, b):
    
    """Return the least common multiple, or inf"""
    
    
    # a, b = map(float, (a, b))
    if all(map(float.is_integer, map(float, (a, b)))) and any((a, b)):
        a, b = map(int, (a, b))
        return float(abs(a*b) // math.gcd(a, b))
    else:
        return float('nan')


def timestamp(unix_time=None, add_usec=True):
    unix_time = unix_time or time.time()
    hh_mm_ss = '%s' % time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(unix_time))
    usec = '%06i' % (1000000 * (unix_time % 1))
    if add_usec:
        return '.'.join((hh_mm_ss, usec))
    else:
        return hh_mm_ss


def list_of_dicts_2_dict_of_dicts(list_of_dicts, key_field):
    dict_of_dicts = {}
    for d in list_of_dicts:
        if key_field in d:
            key = d.pop(key_field)
            dict_of_dicts[key] = d
    return dict_of_dicts


def str_to_list(string):
    if string == NA:
        return []
    else:
        string = string.strip(', ')
        return string.split(',')


def str_to_dict(string):
    string = string.strip(', ')
    if string == NA:
        return {}
    else:
        items = string.split(',')
        items = [i.strip(' ') for i in items]
        return dict((i.split(':') for i in items))


def csv2scsv(s):
    
    """Replace any occurrence of comma in the string with semicolon."""
    
    return s.replace(',', ';')


def default(default_value, suppress=(Exception, ), propagate=()):
    # adapted from https://stackoverflow.com/a/27446895
    # TODO: add a retry n parameter
    def decorator(func):
        def new_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except propagate as e:
                raise e
            except suppress as e:
                return default_value
        return new_func
    return decorator


def shard_name(number_or_metachain):
    if number_or_metachain == 'metachain':
        return 'metachain'
    elif number_or_metachain == NA:
        return NA
    else:
        int_id = int(number_or_metachain)
        if int_id == 0xFFFFFFFF:
            return 'metachain'
        elif int_id < 0:
            raise ValueError('')
        else:
            return 'shard-%i' % int_id


def choose_parser(file_path):
    parsers = {'.json': json.loads,
               '.toml': tomlkit.loads,
               }
    ext = pathlib.Path(file_path).suffix
    return parsers[ext]


def elrond_path(check_exists=True): # FIXME: A lot or all this info is now available from the node API, so use that instad of reading from disk
    """
    Returns a pathlib.Path to the directory where elrond nodes are
    expected to be found.
    
    It assumes the same layout as created by the elrond scripts v2 and
    the node does not need to be running.
    """
    
    elrond_path = pathlib.Path.home() / 'elrond-nodes'
    if check_exists and not elrond_path.is_dir():
        raise RuntimeError("elrond base directory %s doesn't exist" % elrond_path)
    return elrond_path


def number_of_nodes(check_exist=False): # FIXME: A lot or all this info is now available from the node API, so use that instad of reading from disk
    """
    Returns the number of installed elrond nodes.
    
    It assumes the same layout as created by the elrond scripts v2 and
    the node does not need to be running.
    """

    n = int((pathlib.Path().home() / '.numberofnodes').read_text())

    if not check_exist:
        return n
    else:
        _ = (node_path(i, check_exist=True) for i in range(n))
        return n


def node_path(node_number=0, check_exists=False): # FIXME: A lot or all this info is now available from the node API, so use that instad of reading from disk
    """
    Returns a pathlib.Path to the directory where the node is expected 
    to be found.
    
    It assumes the same layout as created by the elrond scripts v2 and
    the node does not need to be running.
    """

    if node_number != abs(int(node_number)):
        raise ValueError('invalid node number %s' % node_number)
    node_path = elrond_path(check_exists) / ('node-%i' % node_number)
    if check_exists and not node_path.is_dir():
        raise RuntimeError("node path %s doesn't exist" % node_path)
    return node_path


def node_binary(node_number=0, check_exists=False): # FIXME: A lot or all this info is now available from the node API, so use that instad of reading from disk
    """
    Returns the expected pathlib.Path to the node binary.
    
    It assumes the same layout as created by the elrond scripts v2 and
    the node does not need to be running.
    """
    
    path = node_path(node_number, check_exists)
    node_binary = path / 'node'
    if check_exists and not path.is_dir():
        raise RuntimeError("node binary %s doesn't exist" % node_binary)
    return node_binary


def logviewer_binary(node_number=0, check_exists=False): # FIXME: A lot or all this info is now available from the node API, so use that instad of reading from disk
    """
    Returns the expected pathlib.Path to the node binary.
    
    It assumes the same layout as created by the elrond scripts v2 and
    the node does not need to be running.
    """
    
    logviewer_binary = pathlib.Path().home() / 'elrond-utils' / 'logviewer'
    if check_exists and not logviewer_binary.is_file():
        raise RuntimeError("logviewer binary %s doesn't exist" % logviewer_binary)
    return logviewer_binary


def config_dir(node_number=0, check_exists=False): # FIXME: A lot or all this info is now available from the node API, so use that instad of reading from disk
    """
    Returns a pathlib.Path to the directory where the node configuration
    files are expected to be found.
    
    It assumes the same layout as created by the elrond scripts v2 and
    the node does not need to be running.
    """
    
    config_dir = elrond_path(check_exists) / ('node-%i' % node_number) / 'config'
    if check_exists and not node_path.is_dir():
        raise RuntimeError("node config directory %s doesn't exist" % config_dir)
    return config_dir


def rest_netloc(node_number=0, host='localhost', first_port=8080):
    """
    Returns a 'host:port' string of the addresses where the node's rest
    interface is expected to be listening.
    
    It assumes nodes are listening on consecutive ports as setup by the
    elrond scripts v2. The node does not need to be running.
    """
    
    return '%s:%i' % (host, first_port + node_number)


def rest_base(node_number=0, host='localhost', first_port=8080):
    """
    Returns a 'http://host:port' string of the addresses where the node's rest
    interface is expected to be listening.
    
    It assumes nodes are listening on consecutive ports as setup by the
    elrond scripts v2. The node does not need to be running.
    """
    
    return 'http://%s' % rest_netloc(node_number, host, first_port)


@default(NA)
def probe_restapi(node_number=0, timeout=1):
    url = rest_base(node_number)
    try:
        urllib.request.urlopen(url, timeout=timeout)
    except urllib.error.HTTPError:
        return True
    except urllib.error.URLError:
        return False
    else:
        return True


@default({}, propagate=(TypeError, ))
def query_route(route, node_number=0, retries=3, timeout=1):
    response = '{}'
    for _ in range(retries):
        url = '/'.join([rest_base(node_number), route])
        with urllib.request.urlopen(url, timeout=timeout) as f:
            response = f.read()
        if response != '{}':
            break
    json.loads(response)
    return json.loads(response)


def node_pid(node_number=0):
    binary = node_binary(node_number, check_exists=True)
    pids = []
    for p in psutil.process_iter():
        try:
            exe = p.exe()
        except psutil.AccessDenied:
            continue
        else:
            if pathlib.Path(exe) == binary:
                pids.append(p.pid)
    if not pids:
        raise RuntimeError('%s is not running' % binary)
    elif len(pids) > 1:  # can multiple instances ever start from same node binary?
        raise RuntimeError('multiple %s running with pids %s' % (binary, pids))
    else:
        return pids.pop()


def running_nodes():
    nodes = {}
    for node_number in range(number_of_nodes(check_exist=False)):
        try:
            pid = node_pid(node_number)
        except RuntimeError:
            continue
        else:
            nodes[node_number] = pid
    return nodes


def best_network_view_node(running_nodes, sync_tolerance=2):
    """
    Return the number, shard and view of the best node to query for network info.
    
    The meaning of 'best' is prioritized like:
       a preferably a synced metachain node,
       b then an unsynced metachain node with nonce > 0
       c then a synced shard node
       d finally an unsynced shard node with nonce > 0

    The race condition from checking sync and shard to actually querying
    for info means e.g. an epoch change or node crash during execution of
    this function or before its outpu is used may result in occasional
    missing data.
    """

    metachain_nodes = set()
    shard_nodes = set()
    synced_nodes = set()

    for node_number in running_nodes:
        
        node_status = query_route('node/status', node_number).get('details', {})
        shard = shard_name(node_status.get('erd_shard_id', NA))
        synced_nonce = node_status.get('erd_nonce', -sync_tolerance)
        probable_highest_nonce = node_status.get('erd_probable_highest_nonce', 1)
        synced = synced_nonce >= (probable_highest_nonce - sync_tolerance)
        
        if shard == 'metachain' and synced_nonce > 0:
            metachain_nodes.add((node_number, shard))
        elif synced_nonce > 0:
            shard_nodes.add((node_number, shard))
        if synced:
            synced_nodes.add((node_number, shard))

    prioritized = {'metachain_synced': metachain_nodes.intersection(synced_nodes),
                   'metachain': metachain_nodes.difference(synced_nodes),
                   'shard_synced': shard_nodes.intersection(synced_nodes),
                   'shard': shard_nodes.difference(synced_nodes),
                   }

    output = [(prio, *node.pop()) for prio, node in prioritized.items() if node] or None
    view, number, shard = output.pop(0) if output else (None, None, None)


    return number, shard, view




def read_config(file_path, value_path, default=None, parser=None):
    file_path = pathlib.Path(file_path)
    parser = parser or choose_parser(file_path)
    keys = value_path.split('/')
    keyvals = parser(file_path.read_text())
    try:
        val = functools.reduce(dict.get, keys, keyvals)
    except TypeError:
        if default:
            return default
        else:
            raise KeyError(keys)
    return val


def read_pubkey(file_path):
    file_path = pathlib.Path(file_path)
    with file_path.open() as f:
        line = f.readline()
    line = line.strip('-\n')
    _, pubkey = line.rsplit(maxsplit=1)
    return pubkey


def hash_file(path, hash_func=hashlib.sha256):
    path = pathlib.Path(path)
    h = hash_func(path.read_bytes())
    return h.hexdigest()


def hash_directory(path, exclude=None, hash_func=hashlib.sha256):
    path = pathlib.Path(path)
    exclude = (exclude) or ()
    files = (f for f in sorted(path.glob('*')) if f.name not in exclude)
    h = hash_func()
    for f in files:
        h.update(f.read_bytes())
    return h.hexdigest()


def get_ip(node_number=0):
    
    q = query_route('node/p2pstatus', node_number).get('details', {}).get('erd_p2p_peer_info', '')
    try:
        addr = [ip for ip in q.split(',') if 'ip4' in ip and '127.0.0.1' not in ip].pop()
        ip = addr.strip('/ip4/').split('/', 1).pop(0)
    except:
        ip = NA
    
    return ip


def get_nic(node_number=0):
    
    ip = get_ip(node_number)
    try:
        nic = [nic for nic, info in psutil.net_if_addrs().items() if ip in str(info)].pop()
    except:
        nic = NA
    
    return nic


def ping(hosts=()):
    
    # TODO: rewrite 
    
    hosts = hosts or ('8.8.8.8', )
    latencies = {}
    for h in hosts:
        try:
            p = sp.Popen(['ping', '-q', '-W 1', '-c 1' '-n', '8.8.8.8'], stdout=PIPE)
        except Exception:
            latencies[h] = NA
        else:
            try:
                l = float(p.communicate()[0].split(b'/0.000')[0].rsplit(b'/', 1)[-1])
            except Exception:
                latencies[h] = NA
            else:
                latencies[h] = l
    
    return latencies


def ntp_sync(service='chrony'):
    
    """Return details of the server NTP time synchronization."""
    
    if service != 'chrony':
        raise NotImplementedError(service)
    
    try:
        r = run(['chronyc', '-c', 'tracking'], timeout=0.1, stdout=PIPE) # hey, this run() is new to me, no more Popen() maybe?
    except Exception:
        return NA
    
    try:
        return dict(((k, v) for k, v
                     in zip(NTP_FIELDS, r.stdout.decode().strip().split(','))
                     if k !='_')
                    )
    except Exception:
        return dict(((k, v) for k, v
                     in zip(NTP_FIELDS, [NA] * len(NTP_FIELDS))
                     if k !='_')
                    )
