import numpy as np 
import os 
import utils.lut_utils as lut_utils
import utils.cnf_utils as cnf_utils
import utils.simulator as simulator
from utils.utils import run_command
from main import main as cnf2lut

def get_all_sat_patterns(bench_path, rpi_list):
    x_data, fanin_list, fanout_list = lut_utils.parse_bench(bench_path)
    pi_list = []
    po_list = []
    for i in range(len(x_data)):
        if len(fanin_list[i]) == 0 and len(fanout_list[i]) != 0:
            pi_list.append(i)
        if len(fanout_list[i]) == 0 and len(fanin_list[i]) != 0:
            po_list.append(i)
    assert len(po_list) == 1
    level_list = lut_utils.get_level(x_data, fanin_list, fanout_list)
    rpi_sat = {}
    
    # Find SAT patterns
    for pattern_idx in range(2 ** len(pi_list)):
        pattern = simulator.dec2list(pattern_idx, len(pi_list))
        states = [-1] * len(x_data)
        for k, pi in enumerate(pi_list):
            states[pi] = pattern[k]
        states = simulator.lut_prog(x_data, level_list, fanin_list, states)
        po_state = states[po_list[0]]
        
        # Check satisfiability of real PI patterns 
        rpi_key = []
        for k in rpi_list:
            rpi_key.append(states[k])
        rpi_key = tuple(rpi_key)
        if rpi_key not in rpi_sat.keys():
            rpi_sat[rpi_key] = po_state
        elif rpi_sat[rpi_key] == 0 and po_state == 1:
            rpi_sat[rpi_key] = 1
    
    return rpi_sat
    

if __name__ == '__main__':
    rpi_list = [0, 1, 2]
    old_bench_path = './tmp/old.bench'
    new_bench_path = './tmp/new.bench'
    old_aig_path = './tmp/old.aig'
    old_cnf_path = './tmp/old.cnf'
    
    for tt_idx in range(2 ** 8):
        if tt_idx == 3:
            print()
        tt = simulator.dec2list(tt_idx, 8)
        tt_hex = simulator.list2hex(tt, 2)
        cmd = 'abc -c \'read_truth {}; strash; write_bench {}; write_aiger {}; print_stats; \''.format(
            tt_hex, old_bench_path, old_aig_path
        )
        stdout_info, _ = run_command(cmd)
        if not 'and' in stdout_info[-2]:
            print('[INFO] Skip: {}\n'.format(tt_hex))
            continue
        cmd = 'aigtocnf {} {}'.format(
            old_aig_path, old_cnf_path
        )
        stdout_info, _ = run_command(cmd)
        cnf2lut(old_cnf_path, new_bench_path)
        
        # Complete Simulation 
        old_res = get_all_sat_patterns(old_bench_path, rpi_list)
        new_res = get_all_sat_patterns(new_bench_path, rpi_list)
        if len(old_res) != 8 or len(new_res) != 8:
            continue
        old_one_cnt = 0
        new_one_cnt = 0
        for key in old_res.keys():
            if old_res[key] == 1:
                old_one_cnt += 1
            if new_res[key] == 1:
                new_one_cnt += 1
            
        print('[INFO] Truth Table: {}'.format(tt_hex))
        print('Old: {}, 1-Count: {:}'.format(old_res, old_one_cnt))
        print('New: {}, 1-Count: {:}'.format(new_res, new_one_cnt))
        print()
        assert old_one_cnt == new_one_cnt
    