import os
import socket
import pathlib
import time
import platform
import psutil # TODO: see if we can remove this dependency
from vilya import utils


NA = 'n/a'


class Record():
    
    """Superclass only for inheriting by actual record implementations."""
    
    name = NotImplemented
    
    def __init__(self):
        self._measure_period = NotImplemented # TODO: read from config file
        self.summarize_period = NotImplemented
        self._res_values = {}
        self._elapsed = 0
        self._last_call_time = 0
        raise NotImplementedError
    
    
    def __call__(self, round_start, do_later_if_skipped=True):
        
        if ((round_start % self.measure_period == 0) or
            do_later_if_skipped and 
            (round_start > self._last_call_time + self.measure_period)):
            
            print(utils.timestamp(),
                  'running', self.name,
                  'for node', self.__dict__.get('node_number', NA)
                  )
            
            res, measure_start = self.measure()
            
            if (self._last_call_time == 0 or # send the field names if it is the first run...
                round_start % 3600 == 0): # ... and on the hour thereafter. TODO: do it at the first opportunity when measure_period is such that the record doesn't always also execute on the hour
                field_names_csv = ','.join(res.keys())
                prepend_field_names_csv = ','.join(('__%s_(%.0f)__' % (self.name,
                                                                     self.measure_period),
                                                    utils.timestamp(measure_start)
                                                    + '~%.6f' % self._elapsed,
                                                    field_names_csv)) + '\n'
            else:
                prepend_field_names_csv = ''
            
            self._last_call_time = round_start
            
            # res_values = {}
            for k, v in res.items():
                if callable(v):
                    val = v()
                else:
                    val = v
                if isinstance(val, (tuple, list)):
                    val = ','.join((str(val) for val in val))
                else:
                    val = str(val)
                self._res_values[k] = val # TODO: keep multiple values for later summarizing
            
            if True:# TODO: round_start % self.summarize_period == 0:
                # TODO: implement summarizing several calls
                res_csv = ','.join(self._res_values.values())
                self._elapsed = max((self._elapsed, time.time() - measure_start))
                output_csv = ','.join((self.name,
                                       utils.timestamp(measure_start) + '~%.6f' % self._elapsed,
                                       res_csv)) + '\n'
                # print(output_csv)
                return prepend_field_names_csv + output_csv
            else:
                return ''
        else:
            return ''
    
    
    @property
    def measure_period(self):
        
        """Return the period and if period was set to 0, change it to inf after the first access."""
        
        if self._measure_period == 0: # this record will run when called for the first time...
            self._measure_period = float('inf') # ... and never again
            return 1
        else:
            return self._measure_period * 6 // 6 # TODO: don't hardcode the round duration
    
    
    def measure(self):
        raise NotImplementedError


class MachineSpecs(Record):
    
    name = 'machine_specs'

    def __init__(self):
        self._measure_period = 0 # TODO: read from config file
        self.summarize_period = NotImplemented
        self._res_values = {}
        self._elapsed = 0
        self._last_call_time = 0
    
    
    def measure(self):
        
        """
        Returns a dictionary of values or functions providing machine status details.
        
        These info are not expected to change while vilya is running
        """
        
        measure_start = time.time()
        
        specs = {
            'host': lambda: socket.getfqdn(),
            'ip': lambda: utils.get_ip(), # TODO: deal with multiple IPs
            'os': lambda: '% s % s' % (platform.uname().system, platform.uname().release),
            'cpu_count': lambda: psutil.cpu_count(logical=False) or 1,  # allows for None when undetermined
            'cpu_treads': lambda: psutil.cpu_count(logical=True) or NA,
            'cpu_clock_max': lambda: round(psutil.cpu_freq().max or psutil.cpu_freq().current),  # some report 0 as max
            'memory_total': lambda: psutil.virtual_memory().total,
            'swap_total': lambda: psutil.swap_memory().total,
            'disk_total': lambda: psutil.disk_usage(str(utils.elrond_path())).total,
        }
        
        return specs, measure_start


class MachineStatus(Record):
    
    name = 'machine_status'
    
    def __init__(self):
        self._measure_period = 1 # TODO: read from config file
        self.summarize_period = NotImplemented
        self._res_values = {}
        self._elapsed = 0
        self._last_call_time = 0
    
    
    def measure(self):
        
        """Returns a dictionary of values or functions providing machine status details."""
    
        measure_start = time.time()
        cpu_t = psutil.cpu_times_percent()
        cpu_load = os.getloadavg()
        ni = utils.get_nic() # assume all nodes are on the same NI of node 0
    
        status = {
            'cpu_load_1': cpu_load[0],
            'cpu_load_5': cpu_load[1],
            'cpu_load_15': cpu_load[2],
            'cpu_t_user': getattr(cpu_t, 'user', NA),
            'cpu_t_system': getattr(cpu_t, 'system', NA),
            'cpu_t_idle': getattr(cpu_t, 'idle', NA),
            'cpu_t_hardirq': NA,  # TODO
            'cpu_t_softirq': getattr(cpu_t, 'softirq', NA),
            'cpu_t_steal': getattr(cpu_t, 'steal', NA),
            'memory_available': lambda: psutil.virtual_memory().available,
            'swap_free': lambda: psutil.swap_memory().free,
            'disk_used': lambda: psutil.disk_usage(str(utils.elrond_path())).used,
            'disk_free': lambda: psutil.disk_usage(str(utils.elrond_path())).free,
            'disk_io_load': NA,  # TODO
            # TODO: deal with multiple NIs? Are all nodes always on the same ip?
            'network_in': lambda: psutil.net_io_counters(pernic=True)[ni].bytes_recv,
            'network_out': lambda: psutil.net_io_counters(pernic=True)[ni].bytes_sent,
            'uptime': lambda: time.time() - psutil.boot_time(),
        }
        
        return status, measure_start


class MachineStatusExtras(Record):
    
    name = 'machine_status_extras'
    
    def __init__(self):
        self._measure_period = 300 # TODO: read from config file
        self.summarize_period = NotImplemented
        self._res_values = {}
        self._elapsed = 0
        self._last_call_time = 0
    
    
    def measure(self):
        
        """Returns a dictionary of values or functions providing machine status details."""
    
        measure_start = time.time()
        ping_status = utils.ping()
        ntp_sync = utils.ntp_sync()
        
        status = {
            # verbatim key-value pairs from other dictionaries
            ** ping_status,
            ** ntp_sync, 
            }
        
        return status, measure_start


class NodeConfig(Record):

    name = 'node_config'
    
    def __init__(self, node_number=0):
        self.node_number = node_number
        self._measure_period = 12 * 3600 # TODO: read from config file
        self.summarize_period = NotImplemented
        self._res_values = {}
        self._elapsed = 0
        self._last_call_time = 0
    
    
    def measure(self):
        
        """Returns a dictionary of functions providing node configuration details.
        
        The node does not need to be running.
        """
    
        measure_start = time.time()
        config_dir = utils.config_dir(self.node_number)
        node_bin = utils.node_binary(self.node_number)
    
        conf = {
            'node_number': self.node_number, # 'node_number' needs to be the first item
            'name': lambda: utils.read_config(config_dir / 'prefs.toml',
                                              'Preferences/NodeDisplayName', NA),
            'public_key': lambda: utils.read_pubkey(config_dir / 'validatorKey.pem'),
            'chain_id': lambda: utils.read_config(config_dir / 'nodesSetup.json',
                                                  'chainID'),
            'round_duration': lambda: utils.read_config(config_dir / 'nodesSetup.json',
                                                        'roundDuration'),
            'rounds_per_epoch': NA,  # TODO
            'genesis_time': lambda: utils.read_config(config_dir / 'nodesSetup.json',
                                                      'startTime'),
            'observer_shard': lambda: utils.shard_name(utils.read_config(config_dir / 'prefs.toml',
                                                                       'Preferences/DestinationShardAsObserver',
                                                                       NA)),
            'version': NA,  # TODO
            'latest_github_version': NA,  # TODO
            'binary_sha256': lambda: utils.hash_file(node_bin),
            'config_sha256': lambda: utils.hash_directory(config_dir,
                                                          exclude=('prefs.toml',
                                                                   'initialNodesSk.pem')),
        }
    
        return conf, measure_start


class NodeStatus(Record):
    
    name = 'node_status'
    
    def __init__(self, node_number):
        self.node_number = node_number
        self._measure_period = 6 # TODO: read from config file
        self.summarize_period = NotImplemented
        self._res_values = {}
        self._elapsed = 0
        self._last_call_time = 0
    
    
    def measure(self):
        
        """Returns a dictionary of functions providing node status details.
        
        The node must be running.
        """
        
        measure_start = time.time()
        node_status = utils.query_route('node/status', self.node_number).get('details', {})
        ip = utils.get_ip(self.node_number)
        ni = utils.get_nic(self.node_number)
        
        status = {
            # calculated values, e.g.
            'node_number': self.node_number, # 'node_number' needs to be the first item
            'ip': ip, 
            'ni': ni, 
            # verbatim key-value pairs from other dictionaries
            ** node_status,
    
            # replace where better formatted values are needed
            'erd_shard_id': utils.shard_name(
                node_status.get('erd_shard_id', NA)),
            'erd_cross_check_block_height': utils.csv2scsv(
                node_status.get('erd_cross_check_block_height', NA)),
            'erd_num_connected_peers_classification': utils.csv2scsv(
                node_status.get('erd_num_connected_peers_classification', NA)),
            
        }
    
        return status, measure_start


class P2pStatus(Record):
    
    name = 'p2p_status'
    
    def __init__(self, node_number=0):
        self.node_number = node_number
        self._measure_period = 600 # TODO: read from config file
        self.summarize_period = NotImplemented
        self._res_values = {}
        self._elapsed = 0
        self._last_call_time = 0
    
    
    def measure(self):
        
        """Returns a dictionary of functions providing node status details.
        
        The node must be running.
        """
        
        measure_start = time.time()
        p2p_status = utils.query_route('node/p2pstatus', self.node_number).get('details', {})
        
        status = {
            # calculated values, e.g.
            'node_number': self.node_number, # 'node_number' needs to be the first item
    
            # better fromatted key-value pairs from other dictionaries
            ** dict(((k, utils.csv2scsv(v)) for k, v in p2p_status.items())), 
        }
    
        return status, measure_start


class NetworkStatus(Record):
    
    name = 'network_status'
    
    def __init__(self, sync_tolerance=2):
        self.sync_tolerance = sync_tolerance
        self._measure_period = 300 # TODO: read from config file
        self.summarize_period = NotImplemented
        self._res_values = {}
        self._elapsed = 0
        self._last_call_time = 0
    
    
    def measure(self):

        """Returns a dictionary of functions providing chain stats details.
        
        A node must be running and sync'd to metachain for full info, if 
        only shard nodes are available, rating info will be missing.
        
        This currently relies on validator/statistics and node/heartbeatstatus
        but I'm not sure node/heartbeatstatus will exist on mainnet.
        """
        
        #TODO: add gather ping times to connected nodes, ref. https://stackoverflow.com/questions/2953462/pinging-servers-in-python
        # and tcp-latency
    
        measure_start = time.time()
        
        node_number, shard, view = utils.best_network_view_node(utils.running_nodes(),
                                                                self.sync_tolerance)
        
        if 'synced' in view:
            heartbeat = utils.query_route('node/heartbeatstatus', node_number).get('message', {})
            if shard == 'metachain':
                network_status = utils.query_route('validator/statistics', node_number).get('statistics', {})
            else:
                network_status = {}
        else:
            heartbeat = network_status = {}
    
        heartbeat = utils.list_of_dicts_2_dict_of_dicts(heartbeat, key_field='publicKey') #  FIXME: returns {}
        public_keys = [pk for pk in heartbeat]
    
        status = {
            'public_keys': public_keys,
    
            ** dict((tag, [network_status.get(pk, {}).get(tag, NA)
                           for pk in public_keys])
                    for tag in network_status[list(network_status).pop()]),
    
            ** dict((tag, [heartbeat.get(pk, {}).get(tag, NA)
                           for pk in public_keys])
                    for tag in heartbeat[list(heartbeat).pop()]),
        }
    
        return status, measure_start


# TODO:
# implement pinging the connected nodes, my other machines, and some well
# known server to monitor network latency. Use ping, tcp - latency and
# maybe some of https://devconnected.com/how-to-ping-specific-port-number/


def main():
    
    """test-run all records and print their outputs"""
    
    records = [MachineSpecs, MachineStatus, NodeConfig, NodeStatus, NetworkStatus]
    
    
    print(time.time())
    
    mc = MachineSpecs()()
    ms = MachineStatus()()
    nc = NodeConfig()(3)
    ns = NodeStatus()(3)
    cs = NetworkStatus()(3)
    print (mc)
    print (ms)
    print (nc)
    print (ns)
    print (cs)
    
    from json import dumps
    for d, timestamp, record_type in (mc, ms, nc, ns, cs):
        print(record_type)
        print(timestamp)
        for key, val in d.items():
            if callable(val):
                val = val()
            try:
                l = len(val)
            except:
                l = -999
            print(l, key, '\t', dumps(val))
        print ('-----------------')
    
    
    print ('=================')    


if __name__ == '__main__':
    import sys
    sys.exit(main())
