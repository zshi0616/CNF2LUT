import numpy as np 
import glob
import os 
import itertools
import copy

from utils.utils import run_command
import utils.cnf_utils as cnf_utils
import utils.clut_utils as clut_utils
import utils.circuit_utils as circuit_utils
from utils.simulator import dec2list, list2hex

cnf_dir = './case/'
NAME_LIST = [
    'l3'
]

LUT_MAX_FANIN = 6
gate_to_index={'PI': 0, 'LUT': 1}
output_dir = './output/'

def check_loop(fanout_list, src, dst):
    visited = [0] * len(fanout_list)
    queue = [src]
    while len(queue) > 0:
        cur = queue.pop(0)
        if cur == dst:
            return True
        visited[cur] = 1
        for fanout in fanout_list[cur]:
            if visited[fanout] == 0:
                queue.append(fanout)
    return False

def divide_long_clauses(cnf, no_var, max_length=4):
    res_cnf = []
    res_no_var = no_var
    for clause in cnf:
        if len(clause) < max_length:
            res_cnf.append(clause)
        else:
            # divide clause based on resolution rules 
            while len(clause) > max_length-1:
                new_var = res_no_var + 1
                res_cnf.append(clause[:max_length-1] + [new_var])
                res_no_var += 1
                clause = [-new_var] + clause[max_length-1:]
            res_cnf.append(clause)
    return res_cnf, res_no_var

def select_cnf(cnf, clause_visited, fanout_idx):
    fanout_var = fanout_idx + 1
    assert fanout_var > 0, 'fanout_idx must be positive'
    var_list = {}
    clauses_contain_fanout = []
    # Find all clauses containing fanout_idx
    for clause_idx, clause in enumerate(cnf):
        if clause_visited[clause_idx] == 1:
            continue
        if fanout_var in clause or -fanout_var in clause:
            clauses_contain_fanout.append(clause_idx)
            for var in clause:
                if abs(var) == fanout_var:
                    continue
                var_list[abs(var)] = 1
    # Find other clauses contained by fan-in var
    for clause_idx, clause in enumerate(cnf):
        if clause_visited[clause_idx] == 1:
            continue
        is_contained = True
        for var in clause:
            if abs(var) not in var_list:
                is_contained = False
                break
        if is_contained:
            clauses_contain_fanout.append(clause_idx)

    # Select maximum covering combination
    var_list = list(var_list.keys())
    if len(var_list) == 0:
        return [], [], []
    elif len(var_list) <= LUT_MAX_FANIN-2:
        best_var_comb = var_list
        best_cover_clauses = clauses_contain_fanout
        cover_cnf = []
        for clause_idx in clauses_contain_fanout:
            cover_cnf.append(cnf[clause_idx])
        best_tt = subcnf_simulation(cover_cnf, var_list, fanout_var)
    else:
        # TODO: Need to improve efficiency
        var_comb_map = {}
        for clause_idx in clauses_contain_fanout:
            clause = cnf[clause_idx]
            var_comb = []
            for var in clause:
                if abs(var) == fanout_var:
                    continue
                var_comb.append(abs(var))
            if len(var_comb) > 0:
                var_comb = tuple(sorted(var_comb))
                if var_comb not in var_comb_map:
                    var_comb_map[var_comb] = [clause_idx]
                else:
                    var_comb_map[var_comb].append(clause_idx)
        
        best_var_comb = []
        best_cover_clauses = []
        best_tt = []
        best_tt_redundant = 4
        for var_comb in var_comb_map:
            if len(var_comb) > LUT_MAX_FANIN-2:
                continue
            cover_clauses = []
            cover_cnf = []
            for clause_idx in var_comb_map[var_comb]:
                cover_clauses.append(clause_idx)
                cover_cnf.append(cnf[clause_idx])
            tt = subcnf_simulation(cover_cnf, var_comb, fanout_var)
            redundant_cnt = 0
            if -1 in tt:
                redundant_cnt += 1
            if 2 in tt:
                redundant_cnt += 1
            if (redundant_cnt < best_tt_redundant) or \
                (redundant_cnt == best_tt_redundant and len(cover_clauses) > len(best_cover_clauses)):
                best_tt_redundant = redundant_cnt
                best_tt = tt
                best_cover_clauses = cover_clauses
                best_var_comb = var_comb
            
    return best_var_comb, best_cover_clauses, best_tt
        
def subcnf_simulation(clauses, var_list, fanout_var):
    truth_table = []
    no_vars = len(var_list)
    for pattern in range(int(pow(2, no_vars))):
        bin_asg = dec2list(pattern, no_vars)
        asg = []
        for idx in range(len(bin_asg)):
            if bin_asg[idx] == 0:
                asg.append(-1 * (var_list[idx]))
            else:
                asg.append(var_list[idx])
        p_eval = cnf_utils.evalute_cnf(clauses, asg + [fanout_var])
        f_eval = cnf_utils.evalute_cnf(clauses, asg + [-fanout_var])
        if p_eval == 0 and f_eval == 0:
            truth_table.append(-1)
        elif p_eval == 0 and f_eval == 1:
            truth_table.append(0)
        elif p_eval == 1 and f_eval == 0:
            truth_table.append(1)
        elif p_eval == 1 and f_eval == 1:
            truth_table.append(2)
    
    return truth_table

def create_lut(lut_tt, lut_fanin_list):
    no_fanin = len(lut_fanin_list)
    lut_len = int(pow(2, no_fanin)) // 4
    # c = !a+b ==> c = 0xD (a, b)
    ordered_lut_fanin = lut_fanin_list[::-1]
    tt_hex = list2hex(lut_tt[::-1], lut_len)
    return tt_hex, ordered_lut_fanin

def add_extra_and(x_data, fanin_list, and_list): 
    k = 0
    while k < len(and_list): 
        extra_and_idx = len(x_data)
        if k + 3 < len(and_list):
            x_data.append([extra_and_idx, gate_to_index['LUT'], '8000'])
            fanin_list.append([and_list[k], and_list[k+1], and_list[k+2], and_list[k+3]])
            and_list.append(extra_and_idx)
            k += 4
        elif k + 2 < len(and_list):
            x_data.append([extra_and_idx, gate_to_index['LUT'], '80'])
            fanin_list.append([and_list[k], and_list[k+1], and_list[k+2]])
            and_list.append(extra_and_idx)
            k += 3
        elif k + 1 < len(and_list):
            x_data.append([extra_and_idx, gate_to_index['LUT'], '8'])
            fanin_list.append([and_list[k], and_list[k+1]])
            and_list.append(extra_and_idx)
            k += 2
        else:
            # print('[INFO] PO: %d' % and_list[k])
            break
    return x_data, fanin_list, and_list[k]

def convert_cnf_xdata(cnf, po_var, no_vars):
    x_data = []     # [name, is_lut, tt]
    fanin_list = []
    fanout_list = []
    has_lut = [0] * no_vars
    clause_visited = [0] * len(cnf)
    extra_po = []
    extra_pi = []
    po_idx = po_var - 1
    map_inv_idx = {}
    
    # Consider the unit clause as PO, generate LUT for po_var at first
    lut_queue = []
    lut_queue.append(po_idx)
    has_lut[po_idx] = 1
    
    # Create gate 
    for k in range(1, no_vars + 1):
        x_data.append([k-1, gate_to_index['PI'], ''])
        fanin_list.append([])
        fanout_list.append([])
    
    while len(lut_queue) > 0:
        lut_idx = lut_queue.pop(0)
        # Select clauses for LUT generation
        var_comb, cover_clauses, tt = select_cnf(cnf, clause_visited, lut_idx)
        if len(var_comb) == 0:
            # print('[DEBUG] LUT %d has no clauses, consider as PI' % lut_idx)
            continue
        lut_fanin_list = []
        for var in var_comb:
            lut_fanin_list.append(var-1)
        
        for idx in lut_fanin_list:
            if not has_lut[idx]:
                lut_queue.append(idx)
                has_lut[idx] = 1
                
        # Parse 3-lut tt: 2 - Don't Care / -1 - Not Available State 
        if 2 in tt:
            new_fanin_idx = len(x_data)
            extra_pi.append(len(x_data))
            x_data.append([new_fanin_idx, gate_to_index['PI'], ''])
            fanin_list.append([])
            fanout_list.append([])
            lut_fanin_list.append(new_fanin_idx)
            new_tt = []
            for k in range(len(tt)):
                if tt[k] == 2:
                    new_tt.append(0)
                    new_tt.append(1)
                else:
                    new_tt.append(tt[k])
                    new_tt.append(tt[k])
            tt = new_tt
        if -1 in tt:
            add_fanout_tt = [1] * len(tt)
            for k in range(len(tt)):
                if tt[k] == -1:
                    add_fanout_tt[k] = 0
                    tt[k] = 0       # 2 means don't care, if unsupport in LUT parser, use 0 
            new_fanout_idx = len(x_data)
            extra_po.append(new_fanout_idx)
            tt_hex, ordered_lut_fanin_idx = create_lut(add_fanout_tt, lut_fanin_list)
            x_data.append([new_fanout_idx, gate_to_index['LUT'], tt_hex])
            fanout_list.append([])
            fanin_list.append([])
            fanin_list[new_fanout_idx] = ordered_lut_fanin_idx
            for fanin_idx in ordered_lut_fanin_idx:
                fanout_list[fanin_idx].append(new_fanout_idx)
                
        ####################################
        # Add LUT 
        ####################################
        # print('LUT Index: {:}, # Nodes in Queue: {:}, Remains: {:} / {:} = {:.2f}%'.format(
        #     lut_idx, len(lut_queue), 
        #     len(cnf) - sum(clause_visited), len(cnf), 
        #     (1 - sum(clause_visited) / len(cnf)) * 100
        # ))
        if len(tt) == 2 and tt[0] == 0 and tt[1] == 1:
            if lut_fanin_list[0] not in map_inv_idx:
                map_inv_idx[lut_fanin_list[0]] = lut_idx
        tt_hex, ordered_lut_fanin_idx = create_lut(tt, lut_fanin_list)
        x_data[lut_idx] = [lut_idx, gate_to_index['LUT'], tt_hex]
        has_loop = False
        for k in ordered_lut_fanin_idx:
            # Check slides for loop detection
            if check_loop(fanout_list, lut_idx, k):
                deloop_idx = len(x_data)
                x_data.append([deloop_idx, gate_to_index['LUT'], tt_hex])
                fanin_list.append([])
                fanout_list.append([])
                fanin_list[deloop_idx] = ordered_lut_fanin_idx
                for fanin_idx in ordered_lut_fanin_idx:
                    fanout_list[fanin_idx].append(deloop_idx)
                deloop_xnor = len(x_data)
                x_data.append([deloop_xnor, gate_to_index['LUT'], '9'])
                fanin_list.append([lut_idx, deloop_idx])
                fanout_list.append([])
                extra_po.append(deloop_xnor)
                has_loop = True
                break
        if not has_loop:
            fanin_list[lut_idx] = ordered_lut_fanin_idx
            for fanin_idx in ordered_lut_fanin_idx:
                fanout_list[fanin_idx].append(lut_idx)
        
        for clause_idx in cover_clauses:
            clause_visited[clause_idx] = 1
    
    for clause_k in range(len(clause_visited)):
        if clause_visited[clause_k] == 0:
            # print('[INFO] Find unassigned clauses, append to PO')
            unassigned_clause = cnf[clause_k]
            extra_and_list = []
            for var in unassigned_clause: 
                node_idx = abs(var) - 1
                if var > 0:
                    extra_and_list.append(node_idx)
                elif node_idx in map_inv_idx:
                    extra_and_list.append(map_inv_idx[node_idx])
                else:
                    extra_not = len(x_data)
                    x_data.append([extra_not, gate_to_index['LUT'], '1'])
                    fanin_list.append([node_idx])
                    map_inv_idx[node_idx] = extra_not
                    extra_and_list.append(map_inv_idx[node_idx])
            x_data, fanin_list, and_idx = add_extra_and(x_data, fanin_list, extra_and_list)
            extra_po.append(and_idx)
    
    # if 0 in clause_visited:
    #     print('[WARNING] Some clauses are not covered')
        
    # Finish converting 
    # print('Finish converting')
    return x_data, fanin_list, po_idx, extra_pi, extra_po

def main(cnf_path, output_bench_path):
    # Read CNF 
    init_cnf, no_vars = cnf_utils.read_cnf(cnf_path)
    init_cnf, no_vars = divide_long_clauses(init_cnf, no_vars, LUT_MAX_FANIN-2)
    no_clauses = len(init_cnf)
    init_cnf = cnf_utils.sort_cnf(init_cnf)
    all_cnf = []
    all_x_data = []
    all_fanin_list = []
    all_po_idx = []
    
    # Ensure there is at least one unit clause
    # assert len(cnf[0]) == 1, 'CNF does not have unit clause' 
    if len(init_cnf[0]) != 1:        # No unit clause, divide into two CNFs
        div_var = init_cnf[0][0]
        cnf_pos = init_cnf + [[div_var]]
        cnf_neg = init_cnf + [[-div_var]]
        all_cnf.append(cnf_pos)
        all_cnf.append(cnf_neg)
    else:
        all_cnf.append(init_cnf)
        
    # Convert to LUT
    assert len(all_cnf) == 1 or len(all_cnf) == 2
    for cnf in all_cnf:
        # If the unit clause is negative, reverse the literal in CNF
        po_var = cnf[0][0]
        reverse_flag = False
        if po_var < 0:
            reverse_flag = True
            for clause_idx in range(len(cnf)):
                for var_idx in range(len(cnf[clause_idx])):
                    if abs(cnf[clause_idx][var_idx]) == abs(po_var):
                        cnf[clause_idx][var_idx] = -cnf[clause_idx][var_idx]
            po_var = -po_var
        x_data, fanin_list, po_idx, extra_pi, extra_po = convert_cnf_xdata(cnf[1:], po_var, no_vars)
        
        # Final PO = AND(PO, extra_po)
        extra_po.append(po_idx)
        x_data, fanin_list, _ = add_extra_and(x_data, fanin_list, extra_po)
        all_x_data.append(x_data)
        all_fanin_list.append(fanin_list)
        all_po_idx.append(extra_po[-1])
        
    x_data = []
    fanin_list = []
    po_indexs = []
    for k in range(len(all_x_data)):
        if k == 0:
            x_data = copy.deepcopy(all_x_data[k])
            fanin_list = copy.deepcopy(all_fanin_list[k])
            po_indexs.append(all_po_idx[k])
        else:
            for x_data_info in all_x_data[k]:
                x_data_info[0] = len(all_x_data[0]) + x_data_info[0]
                x_data.append(x_data_info)
            for fanin_list_info in all_fanin_list[k]:
                new_fanin_list_info = []
                for fanin_idx in fanin_list_info:
                    new_fanin_list_info.append(len(all_x_data[0]) + fanin_idx)
                fanin_list.append(new_fanin_list_info)
            po_indexs.append(len(all_x_data[0]) + all_po_idx[k])
            # OR gate
            extra_or_idx = len(x_data)
            x_data.append([extra_or_idx, gate_to_index['LUT'], 'e'])
            fanin_list.append(po_indexs)

    # Statistics
    no_lut = 0
    no_pi = 0
    for idx in range(len(x_data)):
        if x_data[idx][1] == 1:
            no_lut += 1
        else:
            no_pi += 1
    print('[INFO] # PIs: {:}, # LUTs: {:}'.format(no_pi, no_lut))
    print('[INFO] Save: {}'.format(output_bench_path))
    fanout_list = clut_utils.get_fanout_list(x_data, fanin_list)
    clut_utils.save_clut(output_bench_path, x_data, fanin_list, fanout_list)

if __name__ == '__main__':
    for cnf_path in glob.glob(os.path.join(cnf_dir, '*.cnf')):
        cnf_name = cnf_path.split('/')[-1].split('.')[0]
        if cnf_name not in NAME_LIST:
            continue
        print('Processing %s' % cnf_name)
        output_path = os.path.join(output_dir, cnf_name + '.bench')
        main(cnf_path, output_path)
        
        
    
        
    