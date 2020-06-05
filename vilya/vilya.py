#!/usr/bin/env python

from tomlkit import parse
from vilya import records
from vilya import utils
from vilya.utils import timestamp
import time

import sys
import os
import time
import pathlib
# from itertools import count
from functools import partial
from subprocess import PIPE, Popen
# from collections.abc import Iterable
import threading
# from queue import Queue, Empty, Full

# from random import random


class VilyaError(Exception): pass
class RoundTimeOverrunError(VilyaError): pass
class DeadThreadError(VilyaError): pass


def string_contains(match, log_line): # TODO: move to utils
    
    """Equivalent to str.__contains__ and suitable for functools.partial."""
    
    return match in log_line


def round_start_time(unix_time=None): # TODO: move to utils
    unix_time = unix_time or time.time()
    config_dir = utils.config_dir()
    genesis = int(utils.read_config(config_dir / 'nodesSetup.json', 'startTime'))
    return unix_time - (unix_time - genesis) % 6


def round_duration(unix_time=None): # TODO: move to utils
    config_dir = utils.config_dir()
    return int(utils.read_config(config_dir / 'nodesSetup.json', 'roundDuration') / 1000)


def remote_log_piper(node_number, level, host, port=22, user=None, path=None, event=None, trigger=None):
    
    path = pathlib.Path(path)
    
    logviewer = utils.logviewer_binary(check_exists=True).as_posix()
    node_netloc = utils.rest_netloc(node_number)
    authority = '@'.join((user, host))
    dest_file = (path / r'logs' / (os.uname().nodename +
                                         '#node-%i_%i_log_' % (node_number, int(time.time())))
                 ).as_posix()
    
    local_logviewer = Popen([logviewer, '--address', node_netloc, '--level', level], stdout=PIPE)
    source_pipe = local_logviewer.stdout
    remote_writer = Popen(["ssh", "-p", str(port), authority, "split -d -a 6 -l 100000", "-", dest_file], stdin=PIPE)# at some point we'll run out of numbers and split errors out, but before that point I'll have found a better way
    sink_pipe = remote_writer.stdin
    
    for line in iter(source_pipe.readline, b''):# '\n'):
        sink_pipe.write(line) # python docs say it's safer to call communicate() ?!?
        sink_pipe.flush()
        # print(node_number, line)
        if b'SUBROUND (END_ROUND) BEGINS' in line:# trigger_func and trigger_func(line):
            # time.sleep(random() *6)
            event.set()
            print('%s event set from node %i' % (timestamp(), node_number))# trigger_queue.put(name)

    print('closing')
    source_pipe.close() # maybe it happens automatically?
    sink_pipe.close() # maybe it happens automatically?


def remote_log_piper_daemon(node_number):
    
    detect_subround_end = partial(string_contains, b'SUBROUND (END_ROUND) BEGINS') # TODO: read from config
    
    level = '*:DEBUG'
    host = 'ns347823.ip-91-121-134.eu'
    port = 22
    user = 'vilya'
    path = '/home/vilya/vilya_data'
    event = threading.Event()
    trigger = detect_subround_end
    
    target=remote_log_piper
    args=(node_number, level, host, port, user, path, event, trigger)

    t = threading.Thread(target=target, args=args)
    t.name = 'node-%i remote logger daemon' % node_number
    t.daemon = True # thread dies with the program
    t.start()
    
    return t.name, t, event, target, args


def remote_record_writer(record, sink_pipe, sink_pipe_lock):
    
    rec = record()
    
    start = time.time()
    print ('****************************', rec, start, rec.measure_period)
    sec_into_period = start % rec.measure_period
    time.sleep(rec.measure_period - sec_into_period)

    while 'forever and ever':
        
        start = time.time()
        
        output_csv = rec(int(start))# rec.measure_period)
        # print(output_csv)

        with sink_pipe_lock:
            sink_pipe.write(output_csv.encode()) # python docs say it's safer to call communicate() ?!?
            sink_pipe.flush()
        
        # print ('wait', int(start), rec.measure_period, time.time())
        time.sleep(max(0, int(start) + rec.measure_period - time.time()))


def remote_record_writer_daemon(record, sink_pipe, sink_pipe_lock):

    target = remote_record_writer
    args=(record, sink_pipe, sink_pipe_lock)
    
    t = threading.Thread(target=remote_record_writer, args=args)
    t.daemon = True
    t.name = 'record %s daemon' % record.name
    t.start()

    return t.name, t, target, args


def main():
    # TODO: this mess should be  turned into a class with methods to add tasks
    # of the various types, start and stop them, keep track of what died and 
    # needs resurrecting, read settings from vilya_conf.toml, logging, & co.
    
################ START WORKING ################

    loggers = {} # this will be useful to automate re-start of dead threads
    events = {}
    
    
    #### SPIN UP DAEMONIC THREADS FOR THE LOGS ####
    for node_number in range(utils.number_of_nodes()):
        name, thread, event, target, args = remote_log_piper_daemon(node_number)
        loggers[node_number] = {'name': name,
                                'thread': thread,
                                'event': event,
                                'target': target,
                                'args': args,
                                }
        events[node_number] = event
        print ('thread', name, 'started', )
    
    
    def resurrect_logger(node_number):

        # TODO: move out of main()
        
        name, thread, event, target, args = remote_log_piper_daemon(node_number)
        loggers[node_number] = {'name': name,
                                'thread': thread,
                                'event': event,
                                'target': target,
                                'args': args,
                                }
        events[node_number] = event
        print (timestamp(), 'thread', name, 'resurrected', )
    

    ###### SPIN UP THE HIGH PRIORITY MONITORING ######
        
    host = 'ns347823.ip-91-121-134.eu'
    port = 22
    user = 'vilya'
    path = '/home/vilya/vilya_data'
    # output_queue = Queue()
    
    path = pathlib.Path(path)
    authority = '@'.join((user, host))
    dest_file = (path / r'records' / (os.uname().nodename +
                                            '_%i_records_' % int(time.time()))
                 ).as_posix()
    remote_writer = Popen(["ssh", "-p", str(port), authority, "split -d -a 6 -l 10000", "-", dest_file], stdin=PIPE)# at some point we'll run out of numbers and split errors out, but before that point I'll have found a better way
    sink_pipe = remote_writer.stdin
    sink_pipe_lock = threading.Lock()
    
    name, thread, target, args = remote_record_writer_daemon(records.MachineStatus,
                                                             sink_pipe,
                                                             sink_pipe_lock)
    print ('thread', name, 'started', )
    
    
    ####### DEFINE THE LOW PRIORITY MONITORING #######
    
    # priority is from first to last in the list
    low_priority = [*(records.NodeStatus(node_number)
                      for node_number in range(utils.number_of_nodes())),
                    records.MachineStatusExtras(), 
                    # records.NetworkStatus(),
                    *(records.P2pStatus(node_number)
                    for node_number in range(utils.number_of_nodes())),
                    *(records.NodeConfig(node_number)
                    for node_number in range(utils.number_of_nodes())),
                    records.MachineSpecs(), 
                    ]
    
    
    while 'forever, the scheduler loop never ends':
        
        print('   ¤¤¤¤¤¤¤¤¤¤¤¤¤§§§§§§§§§§§§', 'scheduler starting', '§§§§§§§§§§§§¤¤¤¤¤¤¤¤¤¤¤¤¤¤', '\n')
        
        
        # don't do anything in the main thread for these many seconds into a round
        keepout = 1
        
        # maximum time in seconds before the start of the next round within which a 
        # node claiming to be done with the next round is accepted into the next round
        margin = 0.5
        
        for n in loggers:
            if not loggers[n]['thread'].is_alive():
                print('resurrect logger thread for node', n)
                resurrect_logger(n)
        
        #TODO: check and resurrect remote record thread too
    
    #   try:
        while 'no thread has died':
            
            now = time.time()
            round_start = round_start_time(now)# TODO: round_start_time internally reads from disk every time, do it only after thread crashes (new version)
            sec_into_round = now - round_start
            # if sec_into_round > round_duration() - margin:
                # round_start = round_start_time(now + margin)
                
            print()
            print(timestamp(), '==== loop for round starting at %s ====' %
                  timestamp(round_start, add_usec=False))
            print([t.name for t in threading.enumerate()])
            print('====================================================')
    
            finished = []
            
            # sec_into_round = time.time() - round_start
            if sec_into_round < keepout: # stay out of the way during the 1st second
                print(timestamp(), 'wait until 1 second after round start')
                time.sleep(keepout - sec_into_round)
            if sec_into_round > round_duration() - margin: # skip if the round is almost finished
                print(timestamp(), 'wait for the next round to start')
                # time.sleep(round_duration() - sec_into_round - margin)
                for n in (n for n in events):
                    e = events[n]
                    e.clear()
                time.sleep(max(0, (round_duration() - sec_into_round)))
                continue
            
            print(timestamp(), 'start waiting for nodes to finish processing block')
            
            try:
                for n in (n for n in events):
                    e = events[n]
                    sec_into_round = time.time() - round_start
                    timeout = (round_duration() - sec_into_round - margin)
                    res = e.wait(timeout)
                    e.clear()
                    print (timestamp(), n, res)
                    if not res:
                        print(timestamp(), 'timed out while waiting for node', n)
                        if loggers[n]['thread'].is_alive():
                            raise RoundTimeOverrunError()
                        else:
                            print(timestamp(), 'dead logger for node', n)
                            raise DeadThreadError()
                    else:
                        finished.append(n)
            except RoundTimeOverrunError:
                continue
            except DeadThreadError:
                break
            
            sec_into_round = time.time() - round_start
            if sec_into_round > round_duration() - margin:
                print(timestamp(), 'not enough time left for anything useful')
                print(timestamp(), '!!! loop restart !!!\n')
                continue
            else:
                print(timestamp(), finished)
                print(timestamp(), 'waited succesfully: can do something optional')
                
                
                #### do optional work ####

                for rec in low_priority:
                    output_csv = rec(round_start)
                    if output_csv: # it is '' when it is not time for this record
                        with sink_pipe_lock:
                            sink_pipe.write(output_csv.encode())  # python docs say it's safer to call communicate() ?!?
                            sink_pipe.flush()
                    
                    sec_into_round = time.time() - round_start
                    if sec_into_round > round_duration() - margin: break
                
                #######################

            sec_into_round = time.time() - round_start
            time.sleep(max(0, round_duration() - sec_into_round))

                
            print(timestamp(), '___ loop bottom ___')
                
    #   except Exception:
    #       TODO: log the error and keep going
    #       pass

if __name__ == '__main__':
    sys.exit(main())
