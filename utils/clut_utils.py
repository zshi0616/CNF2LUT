'''
Utility functions for Look-up-table
Author: Stone
'''
import time
import copy
import numpy as np 
import os 

def read_file(file_name):
    f = open(file_name, "r")
    data = f.readlines()
    return data

def get_fanout_list(x_data, fanin_list):
    fanout_list = []
    for idx in range(len(x_data)):
        fanout_list.append([])
    for idx in range(len(x_data)):
        for fanin_idx in fanin_list[idx]:
            fanout_list[fanin_idx].append(idx)
    return fanout_list

def save_clut(filepath, x_data, fanin_list, fanout_list, const_1_list=[]):
    pi_list = []
    po_list = []
    for idx in range(len(x_data)):
        if len(fanin_list[idx]) == 0 and len(fanout_list[idx]) != 0:
            pi_list.append(idx)
        if len(fanout_list[idx]) == 0 and len(fanin_list[idx]) != 0:
            po_list.append(idx)
    
    # Save 
    f = open(filepath, "w")
    for pi_idx in pi_list:
        f.write('INPUT(N' + str(pi_idx) + ')\n')
    for po_idx in po_list:
        if po_idx in const_1_list:
            f.write('OUTPUT(N' + str(po_idx) + ')    # Const_1 \n')
        else:
            f.write('OUTPUT(N' + str(po_idx) + ')\n')
    for idx in range(len(x_data)):
        if idx in const_1_list and idx not in po_list:
            f.write('OUTPUT(N' + str(idx) + ')    # Const_1 \n')
    # for idx in range(len(x_data)):
    #     f.write('OUTPUT(N' + str(idx) + ')\n')
    
    # Save Gate 
    for idx in range(len(x_data)):
        if len(fanin_list[idx]) != 0:
            if x_data[idx][1] == 1:
                gate_line = 'N{} = LUT 0x{} ('.format(idx, x_data[idx][2])
            elif x_data[idx][1] == 2:
                gate_line = 'N{} = AND ('.format(idx)
            else:
                raise Exception('[ERROR] Unknown gate type {}'.format(x_data[idx][1]))
            for k, fanin_idx in enumerate(fanin_list[idx]):
                gate_line += 'N{}'.format(str(fanin_idx))
                if k != len(fanin_list[idx]) - 1:
                    gate_line += ', '
                else:
                    gate_line += ')\n'
            f.write(gate_line)
    
    f.close()