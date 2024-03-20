from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time

class Logger(object):
    def __init__(self, log_path):
        time_str = time.strftime('%Y-%m-%d-%H-%M')
        self.log = open(log_path, 'w')
        self.log.write('Start Time: {:}\n'.format(time_str))
        self.log.write('='*20 + '\n')
        self.log.flush()

    def write(self, txt=''):
        self.log.write(txt)
        self.log.write('\n')
        self.log.flush()
        print(txt)

    def close(self):
        self.log.close()

