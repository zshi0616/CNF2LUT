import numpy as np 
import glob
import os 
import itertools
import copy
import time
from collections import Counter

from utils.utils import run_command
import utils.cnf_utils as cnf_utils
import utils.clut_utils as clut_utils
import utils.circuit_utils as circuit_utils
from utils.simulator import dec2list, list2hex
from itertools import combinations
from line_profiler import LineProfiler

import sys
sys.setrecursionlimit(100000)

cnf_dir = './case/'
NAME_LIST = [
    'brent_13_0_1', 'brent_15_0_25', 'h5'
    # 'a28'
    # 'tt_7'
    # 'mchess16-mixed-45percent-blocked'
]

LUT_MAX_FANIN = 5
gate_to_index={'PI': 0, 'LUT': 1}
output_dir = './output/'

def var_count(cnf, no_vars):
    var_cnts = [0] * (no_vars + 1)
    for clause in cnf:
        for var in clause:
            var_cnts[abs(var)] += 1
    return var_cnts

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

def get_var_comb_map(cnf):
    var_comb_map = {}
    for clause_idx, clause in enumerate(cnf):
        if len(clause) > LUT_MAX_FANIN:
            continue
        var_comb = []
        for var in clause:
            var_comb.append(abs(var))
        var_comb = tuple(sorted(var_comb))
        if var_comb not in var_comb_map:
            var_comb_map[var_comb] = [clause_idx]
        else:
            var_comb_map[var_comb].append(clause_idx)
    
    # Find sub var_comb
    for var_comb in var_comb_map.keys():
        for sub_var_len in range(1, len(var_comb)):
            sub_var_comb_list = list(combinations(var_comb, sub_var_len))
            for sub_var_comb in sub_var_comb_list:
                if sub_var_comb in var_comb_map:
                    var_comb_map[var_comb] += var_comb_map[sub_var_comb]
    
    # Sort by the number of clauses
    var_comb_map = {k: v for k, v in sorted(var_comb_map.items(), key=lambda item: len(item[1]), reverse=True)}
    
    # Var2Varcomb
    var2varcomb_map = {}
    for var_comb in var_comb_map.keys():
        for var in var_comb:
            if var not in var2varcomb_map:
                var2varcomb_map[var] = [var_comb]
            else:
                var2varcomb_map[var].append(var_comb)
                
    return var_comb_map, var2varcomb_map

def select_cnf(cnf, clause_visited, fanout_idx, var_comb_map, var2varcomb_map):
    fanout_var = fanout_idx + 1
    assert fanout_var > 0, 'fanout_idx must be positive'
    if fanout_var not in var2varcomb_map:
        return [], [], []
    var_comb_list = var2varcomb_map[fanout_var]

    # Find joint var_comb (1, 4, 7) (1, 5) ==> (1, 4, 5, 7)
    res_clauses = []
    res_clauses_index = []
    res_var_comb = []
    res_tt = []
    for var_comb in var_comb_list:
        var_comb_wo_fanout = list(var_comb)
        var_comb_wo_fanout.remove(fanout_var)
        tmp_var_comb = list(set(res_var_comb + var_comb_wo_fanout))
        if len(tmp_var_comb) <= LUT_MAX_FANIN+1:
            for clause_idx in var_comb_map[var_comb]:
                if clause_visited[clause_idx] == 1:
                    continue
                res_var_comb = tmp_var_comb
                res_clauses_index.append(clause_idx)
                res_clauses.append(cnf[clause_idx])
    if len(res_var_comb) == 0:
        return [], [], []
    else:
        res_var_comb = sorted(res_var_comb)
        res_tt = subcnf_simulation(res_clauses, res_var_comb, fanout_var)
        return res_var_comb, res_clauses_index, res_tt
        
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

def add_extra_and(x_data, fanin_list, fanout_list, and_list): 
    k = 0
    while k < len(and_list): 
        extra_and_idx = len(x_data)
        if k + 3 < len(and_list):
            x_data.append([extra_and_idx, gate_to_index['LUT'], '8000'])
            fanin_list.append([and_list[k], and_list[k+1], and_list[k+2], and_list[k+3]])
            fanout_list.append([])
            and_list.append(extra_and_idx)
            k += 4
        elif k + 2 < len(and_list):
            x_data.append([extra_and_idx, gate_to_index['LUT'], '80'])
            fanin_list.append([and_list[k], and_list[k+1], and_list[k+2]])
            fanout_list.append([])
            and_list.append(extra_and_idx)
            k += 3
        elif k + 1 < len(and_list):
            x_data.append([extra_and_idx, gate_to_index['LUT'], '8'])
            fanin_list.append([and_list[k], and_list[k+1]])
            fanout_list.append([])
            and_list.append(extra_and_idx)
            k += 2
        else:
            # print('[INFO] PO: %d' % and_list[k])
            break
    return x_data, fanin_list, fanout_list, and_list[k]

def add_extra_or(x_data, fanin_list, fanout_list, or_list):
    k = 0
    while k < len(or_list):
        extra_or_idx = len(x_data)
        if k + 3 < len(or_list):
            x_data.append([extra_or_idx, gate_to_index['LUT'], 'fffe'])
            fanin_list.append([or_list[k], or_list[k+1], or_list[k+2], or_list[k+3]])
            fanout_list.append([])
            or_list.append(extra_or_idx)
            k += 4
        elif k + 2 < len(or_list):
            x_data.append([extra_or_idx, gate_to_index['LUT'], 'fe'])
            fanin_list.append([or_list[k], or_list[k+1], or_list[k+2]])
            fanout_list.append([])
            or_list.append(extra_or_idx)
            k += 3
        elif k + 1 < len(or_list):
            x_data.append([extra_or_idx, gate_to_index['LUT'], 'e'])
            fanin_list.append([or_list[k], or_list[k+1]])
            fanout_list.append([])
            or_list.append(extra_or_idx)
            k += 2
        else:
            # print('[INFO] PO: %d' % or_list[k])
            break
    return x_data, fanin_list, fanout_list, or_list[k]

def traverse_graph(no_vars, x_data, visited, fanin_list, fanout_list, extra_pi, extra_po, node):
    for k, fanin_node in enumerate(fanin_list[node]):
        if 0 <= fanin_node < no_vars:
            if not visited[node][k]:
                visited[node][k] = True
                traverse_graph(no_vars, x_data, visited, fanin_list, fanout_list,extra_pi, extra_po, fanin_node)
            else:
                # Add PI 
                deloop_pi = len(x_data)
                x_data.append([deloop_pi, gate_to_index['PI'], ''])
                fanin_list.append([])
                fanout_list.append([])
                fanout_list[deloop_pi].append(node)
                for fanin_k in range(len(fanin_list[node])):
                    if fanin_list[node][fanin_k] == fanin_node:
                        fanin_list[node][fanin_k] = deloop_pi
                
                # Add XNOR LUT 
                deloop_xnor = len(x_data)
                x_data.append([deloop_xnor, gate_to_index['LUT'], '9'])
                fanin_list.append([fanin_node, deloop_pi])
                fanout_list.append([])
                for fanout_k in range(len(fanout_list[fanin_node])):
                    if fanout_list[fanin_node][fanout_k] == node:
                        fanout_list[fanin_node][fanout_k] = deloop_xnor
                fanout_list[deloop_pi].append(deloop_xnor)
                extra_po.append(deloop_xnor)
                        
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
    # allfo_dict = {}
    # for idx in range(no_vars):
    #     allfo_dict[idx] = []
    
    # Assign the var with maximum occurrence as PO
    var_cnts = var_count(cnf, no_vars)
    var_arglist = np.argsort(var_cnts)[::-1]
    # po_idx = var_arglist[0] - 1
    
    # Preprocess 
    var_comb_map, var2varcomb_map = get_var_comb_map(cnf)
    
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
        var_comb, cover_clauses, tt = select_cnf(cnf, clause_visited, lut_idx, var_comb_map, var2varcomb_map)
        if len(var_comb) == 0:
            # print('[DEBUG] LUT %d has no clauses, consider as PI' % lut_idx)
            continue
        lut_fanin_list = []
        # print('LUT %d: %s' % (lut_idx, var_comb))
        
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
        
        if len(tt) == 2 and tt[0] == 0 and tt[1] == 1:
            if lut_fanin_list[0] not in map_inv_idx:
                map_inv_idx[lut_fanin_list[0]] = lut_idx
        tt_hex, ordered_lut_fanin_idx = create_lut(tt, lut_fanin_list)
        x_data[lut_idx] = [lut_idx, gate_to_index['LUT'], tt_hex]
        

        fanin_list[lut_idx] = ordered_lut_fanin_idx
        for fanin_idx in ordered_lut_fanin_idx:
            fanout_list[fanin_idx].append(lut_idx)
        
        for clause_idx in cover_clauses:
            clause_visited[clause_idx] = 1
    
    for clause_k in range(len(clause_visited)):
        if clause_visited[clause_k] == 0:
            # print('[INFO] Find unassigned clauses, append to PO')
            unassigned_clause = cnf[clause_k]
            
            # TODO: Consider as another circuit AND with this circuit 
            # Now just append unconnected clauses to PO 
            extra_or_list = []
            for var in unassigned_clause:
                node_idx = abs(var) - 1
                if var > 0:
                    extra_or_list.append(node_idx)
                elif node_idx in map_inv_idx:
                    extra_or_list.append(map_inv_idx[node_idx])
                else:
                    extra_not = len(x_data)
                    x_data.append([extra_not, gate_to_index['LUT'], '1'])
                    fanin_list.append([node_idx])
                    fanout_list.append([])
                    map_inv_idx[node_idx] = extra_not
                    extra_or_list.append(map_inv_idx[node_idx])
            x_data, fanin_list, fanout_list, or_idx = add_extra_or(x_data, fanin_list, fanout_list, extra_or_list)
            extra_po.append(or_idx)
    
    
    # Check loop 
    visited = []
    for idx in range(no_vars):
        visited.append([False] * len(fanin_list[idx]))
            
    traverse_graph(
        no_vars, x_data, visited, fanin_list, fanout_list, extra_pi, extra_po, po_idx) # last_node initialized as po_idx
    
    # Finish converting 
    # print('Finish converting')
    return x_data, fanin_list, po_idx, extra_pi, extra_po

def cnf2lut(cnf, no_vars):
    # Sort CNF
    no_clauses = len(cnf)
    cnf = cnf_utils.sort_cnf(cnf)
    
    # Assign the var with maximum occurrence as PO
    var_cnts = var_count(cnf, no_vars)
    var_arglist = np.argsort(var_cnts)[::-1]
    po_var = var_arglist[0]

    # Main
    # # Time analysis 
    # p = LineProfiler()
    # p_wrap = p(convert_cnf_xdata)
    # p_wrap(cnf, po_var, no_vars)
    # p.print_stats()
    # exit(0)
    x_data, fanin_list, po_idx, extra_pi, extra_po = convert_cnf_xdata(cnf, po_var, no_vars)
    
    return x_data, fanin_list, extra_po

def main(cnf_path, output_bench_path):
    # Read CNF 
    cnf, no_vars = cnf_utils.read_cnf(cnf_path)
    
    # Main 
    convert_starttime = time.time()
    x_data, fanin_list, extra_po = cnf2lut(cnf, no_vars)
    print('convert time:{}'.format(time.time() - convert_starttime))
    
    # Save 
    fanout_list = clut_utils.get_fanout_list(x_data, fanin_list)
    saveclut_starttime = time.time()
    clut_utils.save_clut(output_bench_path, x_data, fanin_list, fanout_list, const_1_list=extra_po)
    print('saveclut time:{}'.format(time.time() - saveclut_starttime))

if __name__ == '__main__':
    # x_data = [[0, gate_to_index['PI'], 0], [0, gate_to_index['LUT'], '1'], [0, gate_to_index['LUT'], '1'], 
    #           [0, gate_to_index['LUT'], '1'], [0, gate_to_index['LUT'], '1']]
    # no_vars = len(x_data)
    # fanin_list = [[], [0, 3], [1], [2], [2]]
    # fanout_list = [[1], [2], [3, 4], [1], []]
    # visited = [[False] * no_vars for _ in range(no_vars)]
    # extra_pi = []
    # extra_po = []
    
    # traverse_graph(no_vars, x_data, visited, fanin_list, fanout_list, extra_pi, extra_po, 4)
    # print()
    
    for cnf_path in glob.glob(os.path.join(cnf_dir, '*.cnf')):
        cnf_name = cnf_path.split('/')[-1].split('.')[0]
        if cnf_name not in NAME_LIST:
            continue
        print('Processing %s' % cnf_name)
        output_path = os.path.join(output_dir, cnf_name + '.bench')
        
        main(cnf_path, output_path)    
        print(output_path)