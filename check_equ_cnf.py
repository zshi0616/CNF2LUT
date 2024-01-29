import numpy as np 
import os 
import utils.lut_utils as lut_utils
import utils.cnf_utils as cnf_utils
import utils.simulator as simulator

case_name = 'l3'
cnf_path = './case/{}.cnf'.format(case_name)
bench_path = './output/{}.bench'.format(case_name)

if __name__ == '__main__':
    # Read Bench
    x_data, fanin_list, fanout_list = lut_utils.parse_bench(bench_path)
    pi_list = []
    po_list = []
    for i in range(len(x_data)):
        if len(fanin_list[i]) == 0:
            pi_list.append(i)
        if len(fanout_list[i]) == 0:
            po_list.append(i)
    assert len(po_list) == 1
    level_list = lut_utils.get_level(x_data, fanin_list, fanout_list)
    
    # Read CNF
    cnf, no_vars = cnf_utils.read_cnf(cnf_path)
    no_clauses = len(cnf)
    
    # Find CNF satisfable patterns
    no_cnf_patterns = 0
    for pattern_idx in range(2 ** no_vars):
        patterns = simulator.dec2list(pattern_idx, no_vars)
        is_sat = True
        for clause in cnf:
            clause_sat = False
            for lit in clause:
                if patterns[abs(lit)-1] == 1 and lit > 0:
                    clause_sat = True
                    break
                elif patterns[abs(lit)-1] == 0 and lit < 0:
                    clause_sat = True
                    break
            if not clause_sat:
                is_sat = False
                break
        if is_sat:
            print('CNF SAT: ', patterns)
            no_cnf_patterns += 1
    print('==> CNF SAT: {} patterns'.format(no_cnf_patterns))
    print()
    
    
    # Find SAT patterns
    no_lut_patterns = 0
    rpi_list = []
    for pi in pi_list:
        if int(x_data[pi][0][1:]) - 1 < no_vars:
            rpi_list.append(pi)
    rpi_sat = {}
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
    
    for rpi_key in rpi_sat.keys():
        if rpi_sat[rpi_key] == 1:
            print('LUT SAT: ', rpi_key)
            no_lut_patterns += 1
    print('==> LUT SAT: {} patterns'.format(no_lut_patterns))
    
    print()
    