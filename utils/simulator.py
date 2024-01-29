import os
import random
from webbrowser import Elinks
import numpy as np 
import copy

def dec2list(num, no_PIs):
    res = []
    bin_num = bin(num)[2:].zfill(no_PIs)
    for ele in bin_num:
        res.append(int(ele))
    return res

def list2dec(lst):
    tmp_str = ''
    for ele in lst:
        tmp_str += str(ele)
    return int(tmp_str, 2)

def list2hex(lst, length):
    tmp_str = ''
    for ele in lst:
        tmp_str += str(ele)
    res = hex(int(tmp_str, 2))
    res = res[2:].zfill(length)
    return res

def hex2list(hex_str, length):
    res = []
    bin_str = bin(int(hex_str, 16))[2:].zfill(length)
    for ele in bin_str:
        res.append(int(ele))
    return res

def compress_binary_states(bin_states, width=32):
    res = []
    for idx, bin_list in enumerate(bin_states):
        res.append([])
        for w in range(0, len(bin_list), width):
            bin_slice = bin_list[w:w+width]
            res[idx].append(list2dec(bin_slice))
    return res
    
def logic(gate_type, signals, gate_to_index):
    if gate_type == gate_to_index['AND']:
        if 0 in signals:
            res = 0
        elif -1 in signals: 
            res = -1
        else:
            res = 1
    elif gate_type == gate_to_index['NOT']:
        if signals[0] == 0:
            res = 1
        elif signals[0] == 1:
            res = 0
        else:
            res = -1
    elif gate_type == gate_to_index['NAND']:
        if 0 in signals:
            res = 0
        elif -1 in signals: 
            res = -1
        else:
            res = 1
        if res == 0:
            res = 1
        elif res == 1:
            res = 0
    elif gate_type == gate_to_index['OR']:
        if 1 in signals:
            res = 1
        elif -1 in signals: 
            res = -1
        else:
            res = 0
    elif gate_type == gate_to_index['NOR']:
        if 1 in signals:
            res = 1
        elif -1 in signals: 
            res = -1
        else:
            res = 0
        if res == 0:
            res = 1
        elif res == 1:
            res = 0
    elif gate_type == gate_to_index['BUFF']:
        if signals[0] == -1:
            res = -1
        else:
            res = signals[0]
    elif gate_type == gate_to_index['XOR']:
        if -1 in signals:
            res = -1
        else:
            z_count = 0
            o_count = 0
            for s in signals:
                if s == 0:
                    z_count = z_count + 1
                elif s == 1:
                    o_count = o_count + 1
            if z_count == len(signals) or o_count == len(signals):
                res = 0
            else:
                res = 1
    else:
        raise('Unsupport Gate Type: {:}'.format(gate_type))
    
    return res

def seq_simulator(x_data, level_list, fanin_list, gate_to_index, no_patterns=15000, no_clocks=1000):
    PI_indexes = level_list[0]
    retry_clocks = 0
    max_retry = 1e3

    # Record simulation state
    t_00 = [0] * len(x_data)
    t_01 = [0] * len(x_data)
    t_10 = [0] * len(x_data)
    t_11 = [0] * len(x_data)
    prob_1 = [0] * len(x_data)
    tot_clocks = 0
    
    for sim_times in range(no_patterns):
        retry_clocks = 0
        state = [-1] * len(x_data)
        last_state = [-1] * len(x_data)
        if sim_times % 1000 == 0:
            print('[INFO] Simulate # Patterns: {:} k'.format(sim_times / 1000))

        # Initial FF state 
        for node_idx in range(len(x_data)):
            if x_data[node_idx][1] == gate_to_index['DFF']:
                state[node_idx] = random.randint(0, 1)
        
        for clock_idx in range(no_clocks):
            # Generate input patterns 
            state_vec = []
            for x_data_info in x_data:
                state_vec.append([])
            for pi_idx in PI_indexes:
                state[pi_idx] = random.randint(0, 1)

            # Combinational 
            for level in range(1, len(level_list), 1):
                for node_idx in level_list[level]:
                    gate_type = x_data[node_idx][1]
                    if gate_type == gate_to_index['DFF']:
                        continue
                    source_signals = []
                    for pre_idx in fanin_list[node_idx]:
                        source_signals.append(state[pre_idx])
                    if len(source_signals) > 0:
                        res = logic(gate_type, source_signals, gate_to_index)
                        state[node_idx] = res

            # Clock event 
            for node_idx in range(len(x_data)):
                if x_data[node_idx][1] == gate_to_index['DFF']:
                    state[node_idx] = last_state[fanin_list[node_idx][0]]
            
            # Transition
            if -1 in state:
                raise()
                # retry_clocks += 1
                # last_state = copy.deepcopy(state)
                # if retry_clocks > max_retry:
                #     return False, [], [], [], [], []
                # continue
            else:
                tot_clocks += 1
            for node_idx in range(len(x_data)):
                if last_state[node_idx] == 0 and state[node_idx] == 0:
                    t_00[node_idx] += 1
                elif last_state[node_idx] == 0 and state[node_idx] == 1:
                    t_01[node_idx] += 1
                elif last_state[node_idx] == 1 and state[node_idx] == 0:
                    t_10[node_idx] += 1
                elif last_state[node_idx] == 1 and state[node_idx] == 1:
                    t_11[node_idx] += 1

                if state[node_idx] == 1:
                    prob_1[node_idx] += 1
            last_state = copy.deepcopy(state)
    
    
    for node_idx in range(len(x_data)):
        t_00[node_idx] /= tot_clocks
        t_01[node_idx] /= tot_clocks
        t_10[node_idx] /= tot_clocks
        t_11[node_idx] /= tot_clocks
        prob_1[node_idx] /= tot_clocks

    return t_00, t_01, t_10, t_11, prob_1

def comb_prog(x_data, level_list, fanin_list, gate_to_index, state):
    res_state = copy.deepcopy(state)
    for level in range(1, len(level_list), 1):
        for node_idx in level_list[level]:
            gate_type = x_data[node_idx][1]
            if 'DFF' in gate_to_index.keys() and gate_type == gate_to_index['DFF']:
                continue
            source_signals = []
            for pre_idx in fanin_list[node_idx]:
                source_signals.append(res_state[pre_idx])
            if len(source_signals) > 0:
                res = logic(gate_type, source_signals, gate_to_index)
                res_state[node_idx] = res
    return res_state

def get_truth_table(x_data, level_list, fanin_list, no_pi, hex_len, gate_to_index={'INPUT': 0, 'AND': 1, 'NOT': 2}):
    assert len(level_list[-1]) == 1
    po_idx = level_list[-1][0]
    pi_list = level_list[0]
    assert len(pi_list) == no_pi
    pi_patterns = []
    for i in range(2 ** no_pi):
        pi_patterns.append(dec2list(i, no_pi))
    
    tt = []
    for pi_pattern in pi_patterns:
        state = [-1] * len(x_data)
        for idx, pi_idx in enumerate(pi_list):
            state[pi_idx] = pi_pattern[idx]
        state = comb_prog(x_data, level_list, fanin_list, gate_to_index, state)
        tt.append(state[po_idx])
    
    res = list2hex(tt, hex_len)
    return res
    
def lut_prog(x_data, level_list, fanin_list, states): 
    for level in range(1, len(level_list)):
        for node_idx in level_list[level]:
            config_value = x_data[node_idx][1]
            source_signals = []
            for pre_idx in fanin_list[node_idx]:
                source_signals.append(states[pre_idx])
            truth_table = hex2list(config_value, int(pow(2, len(source_signals))))[::-1]
            if len(source_signals) > 0:
                source_signal_tt_index = list2dec(source_signals[::-1])
                states[node_idx] = truth_table[source_signal_tt_index]
    
    return states
