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
    is_pi = [False] * len(x_data)
    is_po = [False] * len(x_data)
    for idx in range(len(x_data)):
        if len(fanin_list[idx]) == 0 and len(fanout_list[idx]) != 0:
            pi_list.append(idx)
            is_pi[idx] = True
        if len(fanout_list[idx]) == 0 and len(fanin_list[idx]) != 0:
            po_list.append(idx)
            is_po[idx] = True
    
    # Const_1 
    is_const_1 = [False] * len(x_data)
    for idx in const_1_list:
        is_const_1[idx] = True
    
    # Save 
    f = open(filepath, "w")
    for pi_idx in pi_list:
        f.write('INPUT(N' + str(pi_idx) + ')\n')
    for po_idx in po_list:
        if is_const_1[po_idx]:
            f.write('OUTPUT(N' + str(po_idx) + ')    # Const_1 \n')
        else:
            f.write('OUTPUT(N' + str(po_idx) + ')\n')
    for idx in range(len(x_data)):
        if is_const_1[idx] and not is_po[idx]:
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


def list2hex(lst, length):
    tmp_str = ''
    for ele in lst:
        tmp_str += str(ele)
    res = hex(int(tmp_str, 2))
    res = res[2:].zfill(length)
    return res
    
def make_and_lut(input_num):
    lut_length = int(pow(2, input_num )) // 4
    # lut_value = 1
    # lut = str(lut_value).zfill(lut_length)
    lut_value = [0]* int(pow(2, input_num ))
    lut_value[0] = 1
    lut = list2hex(lut_value, lut_length)
    return lut
    
And_max_fanin = 8
    
def save_clut_onepo(filepath, x_data, fanin_list, fanout_list, const_1_list=[]):

    input_num = len(const_1_list)
    input_each_layer = []
    input_num_each_layer = []
    if  input_num == 0:
        # TODO
        return
    
    input_idx = const_1_list
    while input_num > And_max_fanin:

        new_input_idx = []
        for i in range(int(input_num/And_max_fanin)):
            lut = make_and_lut(And_max_fanin)
            new_input_idx.append(len(x_data))
            x_data.append([len(x_data),1,lut])
            fanin =[]
            for idx in range( And_max_fanin*i, And_max_fanin*(i+1) ):
                fanin.append(input_idx[idx])
            fanin_list.append(fanin)
            fanout_list.append([])
        # 不够32的部分
        fanin =[]
        for idx in range( int(input_num/And_max_fanin)*And_max_fanin, input_num ):
            fanin.append(input_idx[idx])
        if len(fanin) != 0:
            fanin_list.append(fanin)
            fanout_list.append([])
            lut = make_and_lut(input_num - And_max_fanin * int(input_num/And_max_fanin))
            new_input_idx.append(len(x_data))
            x_data.append([len(x_data),1,lut])
            input_num = int(input_num/And_max_fanin)+1   
        else:
            input_num = int(input_num/And_max_fanin)
        input_idx = new_input_idx

    PO_idx = len(x_data)
    lut = make_and_lut(input_num)
    x_data.append([len(x_data),1,lut])
    fanin =[]
    for idx in range(len(input_idx)):
        fanin.append(input_idx[idx])
    fanin_list.append(fanin)
    fanout_list.append([])
    
    pi_list = []
    po_list = []
    is_pi = [False] * len(x_data)
    is_po = [False] * len(x_data)
    for idx in range(len(x_data)):
        if len(fanin_list[idx]) == 0 and len(fanout_list[idx]) != 0:
            pi_list.append(idx)
            is_pi[idx] = True
        if len(fanout_list[idx]) == 0 and len(fanin_list[idx]) != 0:
            po_list.append(idx)
            is_po[idx] = True
            
    # Const_1 
    is_const_1 = [False] * len(x_data)
    for idx in const_1_list:
        is_const_1[idx] = True
    
    # Save 
    f = open(filepath, "w")
    for pi_idx in pi_list:
        f.write('INPUT(N' + str(pi_idx) + ')\n')
    f.write('OUTPUT(N' + str(PO_idx) + ')\n') 
    
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
