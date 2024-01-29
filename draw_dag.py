import numpy as np 
import deepgate as dg
import glob
import os 
import copy
import itertools
import networkx as nx
import matplotlib.pyplot as plt
import random

from utils.utils import run_command
import utils.cnf_utils as cnf_utils
import utils.clut_utils as clut_utils
import utils.circuit_utils as circuit_utils
from utils.simulator import dec2list, list2hex

cnf_dir = './case/'
NAME_LIST = [
    # 'e13'
    'mult_op_DEMO1_3_3_TOP6'
]

LUT_MAX_FANIN = 6
gate_to_index={'PI': 0, 'LUT': 1}
output_dir = './output/'

def check_loop(fanout_list, src):
    visited = [0] * len(fanout_list)
    queue = [src]
    while len(queue) > 0:
        cur = queue.pop(0)
        if visited[cur] == 1:
            return True
        visited[cur] = 1
        for fanout in fanout_list[cur]:
            queue.append(fanout)
    return False

def select_cnf(cnf, clause_visited, fanout_idx):
    assert fanout_idx > 0, 'fanout_idx must be positive'
    var_list = {}
    clauses_contain_fanout = []
    # Find all clauses containing fanout_idx
    for clause_idx, clause in enumerate(cnf):
        if clause_visited[clause_idx] == 1:
            continue
        if fanout_idx in clause or -fanout_idx in clause:
            clauses_contain_fanout.append(clause_idx)
            for var in clause:
                if abs(var) == fanout_idx:
                    continue
                var_list[abs(var)] = 1
    # Select maximum covering combination
    var_list = list(var_list.keys())
    if len(var_list) <= LUT_MAX_FANIN-2:
        max_cover_list = clauses_contain_fanout
        max_comb = var_list
    else:
        comb_list = list(itertools.combinations(var_list, LUT_MAX_FANIN-2))  # -2 because fanout_idx and possible new fanin
        max_cover_list = []
        max_comb = []
        for comb in comb_list:
            cover_list = []
            for clause_idx in clauses_contain_fanout:
                clause = cnf[clause_idx]
                covered = True
                for var in clause:
                    if abs(var) == fanout_idx:
                        continue
                    if abs(var) not in comb:
                        covered = False
                        break
                if covered:
                    cover_list.append(clause_idx)
            if len(cover_list) > len(max_cover_list):
                max_cover_list = cover_list
                max_comb = comb
    
    # select clauses
    var_map = {}
    for var in max_comb:
        var_map[var] = len(var_map) + 1
    var_map[fanout_idx] = len(var_map) + 1
    map_clauses = []
    for clause_idx in max_cover_list:
        clause = cnf[clause_idx]
        one_clause = []
        for var in clause:
            if var > 0:
                one_clause.append(var_map[var])
            else:
                one_clause.append(-var_map[-var])
        map_clauses.append(one_clause)
    
    return var_map, map_clauses, max_cover_list

def subcnf_simulation(map_clauses, var_map, fanout_idx):
    truth_table = []
    no_vars = len(var_map) - 1
    for pattern in range(int(pow(2, no_vars))):
        bin_asg = dec2list(pattern, no_vars)
        asg = []
        for idx in range(len(bin_asg)):
            if bin_asg[idx] == 0:
                asg.append(-1 * (idx + 1))
            else:
                asg.append(idx + 1)
        p_eval = cnf_utils.evalute_cnf(map_clauses, asg + [var_map[fanout_idx]])
        f_eval = cnf_utils.evalute_cnf(map_clauses, asg + [-var_map[fanout_idx]])
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
    for idx in range(len(ordered_lut_fanin)):
        ordered_lut_fanin[idx] = ordered_lut_fanin[idx] - 1
    return tt_hex, ordered_lut_fanin

def convert_cnf_xdata(cnf, po_var, no_vars):
    x_data = []     # [name, is_lut, tt]
    fanin_list = []
    fanout_list = []
    var_lut_level = [-1] * (no_vars + 1)
    clause_visited = [0] * len(cnf)
    extra_po = []
    extra_pi = []
    po_idx = po_var - 1
    
    lut_queue = []
    lut_queue.append(po_var)
    
    ####################################
    # Debug 
    ####################################
    G = nx.DiGraph()
    for idx in range(1, no_vars + 1):
        G.add_node(idx)
    backward_level = [-1] * (no_vars+1)
    backward_level[po_var] = 0
    
    # Create gate 
    for k in range(1, no_vars + 1):
        x_data.append([k-1, gate_to_index['PI'], ''])
        fanin_list.append([])
        fanout_list.append([])
    
    while len(lut_queue) > 0:
        lut_var = lut_queue.pop(0)
        var_map, map_clauses, selected_clause_index = select_cnf(cnf, clause_visited, lut_var)
        if len(selected_clause_index) == 0:
            print('[DEBUG] LUT %d has no clauses, consider as PI' % lut_var)
            continue
        tt = subcnf_simulation(map_clauses, var_map, lut_var)
        lut_fanin_list = list(var_map.keys())[:-1]
        
        for var in lut_fanin_list:
            if var_lut_level[var] == -1:
                lut_queue.append(var)
                
        ####################################
        # Debug 
        ####################################
        if lut_var == 14 or lut_var == 15:
            print()
        for var in lut_fanin_list:
            G.add_edge(var, lut_var)
            if backward_level[var] == -1 or backward_level[var] > backward_level[lut_var] + 1:
                backward_level[var] = backward_level[lut_var] + 1
                
        # Parse 3-lut tt 
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
            extra_po.append(len(x_data))
            tt_hex, ordered_lut_fanin_idx = create_lut(add_fanout_tt, lut_fanin_list)
            x_data.append([new_fanout_idx, gate_to_index['LUT'], tt_hex])
            fanout_list.append([])
            fanin_list.append([])
            # Check loop 
            for k in range(len(ordered_lut_fanin_idx)):
                if check_loop(fanout_list, ordered_lut_fanin_idx[k]):
                    unloop_pi = len(x_data)
                    unloop_xnor = len(x_data) + 1
                    x_data.append([unloop_pi, gate_to_index['PI'], ''])
                    x_data.append([unloop_xnor, gate_to_index['LUT'], '9'])
                    fanout_list.append([])
                    fanout_list.append([])
                    fanin_list.append([])
                    fanin_list.append([])
                    fanin_list[unloop_xnor] = [unloop_pi, ordered_lut_fanin_idx[k]]
                    fanout_list[unloop_pi].append(unloop_xnor)
                    fanout_list[ordered_lut_fanin_idx[k]].append(unloop_xnor)
                    ordered_lut_fanin_idx[k] = unloop_xnor
                    extra_pi.append(unloop_pi)
                    extra_po.append(unloop_xnor)
                    # print('[DEBUG] Loop detected')
            fanin_list[new_fanout_idx] = ordered_lut_fanin_idx
            for fanin_idx in ordered_lut_fanin_idx:
                fanout_list[fanin_idx].append(new_fanout_idx)
                
        ####################################
        # Add LUT 
        ####################################
        tt_hex, ordered_lut_fanin_idx = create_lut(tt, lut_fanin_list)
        x_data[lut_var-1] = [lut_var-1, gate_to_index['LUT'], tt_hex]
        # Check loop 
        for k in range(len(ordered_lut_fanin_idx)):
            if check_loop(fanout_list, ordered_lut_fanin_idx[k]):
                unloop_pi = len(x_data)
                unloop_xnor = len(x_data) + 1
                x_data.append([unloop_pi, gate_to_index['PI'], ''])
                x_data.append([unloop_xnor, gate_to_index['LUT'], '9'])
                fanout_list.append([])
                fanout_list.append([])
                fanin_list.append([])
                fanin_list.append([])
                fanin_list[unloop_xnor] = [unloop_pi, ordered_lut_fanin_idx[k]]
                fanout_list[unloop_pi].append(unloop_xnor)
                fanout_list[ordered_lut_fanin_idx[k]].append(unloop_xnor)
                ordered_lut_fanin_idx[k] = unloop_xnor
                extra_pi.append(unloop_pi)
                extra_po.append(unloop_xnor)
                # print('[DEBUG] Loop detected')
        fanin_list[lut_var-1] = ordered_lut_fanin_idx
        for fanin_idx in ordered_lut_fanin_idx:
            fanout_list[fanin_idx].append(lut_var-1)
        for clause_idx in selected_clause_index:
            clause_visited[clause_idx] = 1
        
        print(tt)
    
    ####################################
    # Debug 
    ####################################
    max_level = max(backward_level)
    for idx in range(1, no_vars + 1):
        # G.nodes[idx]['level'] = max_level - backward_level[idx]
        G.nodes[idx]['level'] = int(backward_level[idx] * 100 + (random.random() - 0.5) * 10)
    pos = nx.multipartite_layout(G, subset_key="level")
    
    plt.figure(figsize=(40, 20))
    nx.draw_networkx(G, pos=pos, node_size=2000, font_size=30, with_labels=True, node_color='white')
    pdf_filename = './fig/out.pdf'
    plt.savefig(pdf_filename)
    plt.close()
    
    # Finish converting 
    print('Finish converting')
    return x_data, fanin_list, po_idx, extra_pi, extra_po

if __name__ == '__main__':
    for cnf_path in glob.glob(os.path.join(cnf_dir, '*.cnf')):
        cnf_name = cnf_path.split('/')[-1].split('.')[0]
        if cnf_name not in NAME_LIST:
            continue
        print('Processing %s' % cnf_name)
        output_path = os.path.join(output_dir, cnf_name + '.bench')
        
        # Read CNF 
        cnf, no_vars = cnf_utils.read_cnf(cnf_path)
        no_clauses = len(cnf)
        cnf = cnf_utils.sort_cnf(cnf)
        assert len(cnf[0]) == 1, 'CNF does not have unit clause'
        
        # Convert 
        po_var = cnf[0][0]
        x_data, fanin_list, po_idx, extra_pi, extra_po = convert_cnf_xdata(cnf[1:], po_var, no_vars)
        # Final PO 
        extra_and = []
        k = 0
        extra_po.append(po_idx)
        while k < len(extra_po):
            extra_and_idx = len(x_data)
            if k + 3 < len(extra_po):
                x_data.append([extra_and_idx, gate_to_index['LUT'], '8000'])
                fanin_list.append([extra_po[k], extra_po[k+1], extra_po[k+2], extra_po[k+3]])
                extra_po.append(extra_and_idx)
                k += 4
            elif k + 2 < len(extra_po):
                x_data.append([extra_and_idx, gate_to_index['LUT'], '80'])
                fanin_list.append([extra_po[k], extra_po[k+1], extra_po[k+2]])
                extra_po.append(extra_and_idx)
                k += 3
            elif k + 1 < len(extra_po):
                x_data.append([extra_and_idx, gate_to_index['LUT'], '8'])
                fanin_list.append([extra_po[k], extra_po[k+1]])
                extra_po.append(extra_and_idx)
                k += 2
            else:
                print('[INFO] PO: %d' % extra_po[k])
                break
        
        # Statistics
        no_lut = 0
        no_pi = 0
        for idx in range(len(x_data)):
            if x_data[idx][1] == 1:
                no_lut += 1
            else:
                no_pi += 1
        print('# PIs: {:}, # LUTs: {:}'.format(no_pi, no_lut))
        print('Save: {}'.format(output_path))
        clut_utils.save_clut(output_path, x_data, fanin_list)
    
        
    