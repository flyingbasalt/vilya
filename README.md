# vilya

This is Flying Stone's unofficial monitoring (and soon management) tool for [Elrond Network](https://elrond.com) 
[nodes](https://github.com/ElrondNetwork/elrond-go). This package is the agent running on the 
same machine as the node or nodes being monitored.

## Features
Compared to other monitoring solutions, vilya is:

1. secure: all data is sent to a remote machine through the local machine's ssh client, so no need for opening any firewall port, no answering to any requests, no extra software
2. easily auditable: the code is short and with very few dependencies (and they will go away over time), so you can read and understand the code for yourself before installing or updating it
3. easy to use: it was written from scratch for the job, so configuration is minimal and implementing new measurements is easy and fast (you need to write a little python, but it looks almost like a configuration file)
4. lightweight but powerful: it uses less than 1% of th cpu when remotely logging:

   * cpu, memory, disk and network usage every second, plus
   * the node/status API route every round, plus
   * node/p2pstatus, node/heartbeatstatus, validator/statistics every 5-10 minutes, plus
   * the full *:DEBUG log stream
   * more, just read records.py
5. synchronized to the Elrond Network, so it waits until each block has been signed and sent before doing most of its job
6. MIT licensed, because it is the shortest and most permissive of all popular licenses
7. named after Vilya, Elrond's ring and the mightiest of the Three of course :^)

## Status
I've been running it without problem on 3 machines each with 2 to 4 of the flying-... nodes 
over the last few weeks without issues. Its companion dashboard application 
[nodeview](https://pypi.org/project/nodeview) is still a work in progress so vilya changing a bit 
so the two work well with each other.

to install: `$ pip3 install vilya`

_NOTE_: as I'm still developing it, some of the configuration is still hardcoded so installing with 
pip won't work out of the box for now. But if you know a little pythin you can find your way. The 
only other required configuration is to setup the ssh client for accessing the remote machine. More 
instruction will follow with the first realease. I'll soon upload to github, but the code of course 
is already on this page too.



