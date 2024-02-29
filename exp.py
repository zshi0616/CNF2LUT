import os
import numpy as np 
import copy

import utils.aiger_utils as aiger_utils
import utils.circuit_utils as circuit_utils
import utils.cnf_utils as cnf_utils
import utils.lut_utils as lut_utils
from utils.utils import run_command
from main import main as cnf2lut

AIG_DIR = '/Users/zhengyuanshi/studio/dataset/LEC/all_case'
NAME_LIST = [
    "c18", "c17", "d20", "e15", "e2", "e19", "e26", "h21", "d18", "ab40", "ac2", "ad21", "ad41", "ac33", "ad43", "aa22", "ac42", "ad2", "aa5", "f16", "ac25", "ad34", "f28", "ad26", "f21", "ab5", "h30"
]

if __name__ == '__main__':
    for aig_name in NAME_LIST:
        aig_path = os.path.join(AIG_DIR, '{}.aiger'.format(aig_name))
        abc_cmd = 'abc -c \" read_aiger {}; print_stats;\"'.format(aig_path)
        abc_output, _ = run_command(abc_cmd)
        arr = abc_output[-2].replace(' ', '').replace('and', '').replace('lev', '').split('=')
        no_nodes = int(arr[-2])
        no_levels = int(arr[-1])
        # print(aig_name, no_nodes, no_levels)
        print('{},{}'.format(no_nodes, no_levels))
        