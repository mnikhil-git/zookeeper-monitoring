""" Python Ganglia Module for ZooKeeper monitoring 

Inspired by: http://gist.github.com/448007
"""

import sys
import socket
import time

from StringIO import StringIO

TIME_BETWEEN_QUERIES = 20

class ZooKeeperServer(object):

    def __init__(self, host='localhost', port='2181', timeout=1):
        self._address = (host, int(port))
        self._timeout = timeout

    def get_stats(self):
        """ Get ZooKeeper server stats as a map """
        s = self._create_socket()
        s.settimeout(self._timeout)

        s.connect(self._address)
        s.send('mntr')

        data = s.recv(2048)
        s.close()

        return self._parse(data)

    def _create_socket(self):
        return socket.socket()

    def _parse(self, data):
        """ Parse the output from the 'mntr' 4letter word command """
        h = StringIO(data)
        
        result = {}
        for line in h.readlines():
            try:
                key, value = self._parse_line(line)
                result[key] = value
            except ValueError:
                pass # ignore broken lines

        return result

    def _parse_line(self, line):
        try:
            key, value = map(str.strip, line.split('\t'))
        except ValueError:
            raise ValueError('Found invalid line: %s' % line)

        if not key:
            raise ValueError('The key is mandatory and should not be empty')

        try:
            value = int(value)
        except (TypeError, ValueError):
            pass

        return key, value


def metric_handler(name):
    if time.time() - metric_handler.timestamp > TIME_BETWEEN_QUERIES:
        zk = ZooKeeperServer(metric_handler.host, metric_handler.port, 5)
        try:
            metric_handler.info = zk.get_stats()
        except Exception, e:
            print >>sys.stderr, e
            metric_handler.info = {}

    return metric_handler.info.get(name, 0)

def metric_init(params=None):
    params = params or {}

    metric_handler.host = params.get('host', 'localhost')
    metric_handler.port = int(params.get('port', 2181))
    metric_handler.timestamp = 0

    metrics = {
        'zk_avg_latency': {'units': 'ms'},
        'zk_max_latency': {'units': 'ms'},
        'zk_min_latency': {'units': 'ms'},
        'zk_packets_received': {
            'units': 'packets',
            'slope': 'positive'
        },
        'zk_packets_sent': {
            'units': 'packets',
            'slope': 'positive'
        },
        'zk_outstanding_requests': {'units': 'connections'},
        'zk_znode_count': {'units': 'znodes'},
        'zk_watch_count': {'units': 'watches'},
        'zk_ephemerals_count': {'units': 'znodes'},
        'zk_approximate_data_size': {'units': 'bytes'},
        'zk_open_file_descriptor_count': {'units': 'descriptors'},
        'zk_max_file_descriptor_count': {'units': 'descriptors'},
        'zk_followers': {'units': 'nodes'},
        'zk_synced_followers': {'units': 'nodes'},
        'zk_pending_syncs': {'units': 'syncs'}
    }
    metric_handler.descriptors = {}
    for name, updates in metrics.iteritems():
        descriptor = {
            'name': name,
            'call_back': metric_handler,
            'time_max': 90,
            'value_type': 'int',
            'units': '',
            'slope': 'both',
            'format': '%d',
            'groups': 'zookeeper',
        }
        descriptor.update(updates)
        metric_handler.descriptors[name] = descriptor

    return metric_handler.descriptors.values()

def metric_cleanup():
    pass


if __name__ == '__main__':
    ds = metric_init({'host':'localhost', 'port': '2181'})
    for d in ds:
        print "%s=%s" % (d['name'], metric_handler(d['name']))


