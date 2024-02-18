import numpy as np 
import glob
import os 
import itertools

from utils.utils import run_command
import utils.cnf_utils as cnf_utils
import utils.clut_utils as clut_utils
import utils.lut_utils as lut_utils
import utils.aiger_utils as aiger_utils
import utils.circuit_utils as circuit_utils
from utils.simulator import dec2list, list2hex

def hex2list(hex_str):
    bin_str = bin(int(hex_str, 16))[2:]
    bin_str = bin_str[::-1]
    return [int(bit) for bit in bin_str]

def lut2tt(tt_hex, ordered_lut_fanin):
    # tt_hex = '0x' + tt_hex.zfill(len(tt_hex))
    lut_tt = hex2list(tt_hex)
    lut_len = len(lut_tt)
    lut_fanin_list = ordered_lut_fanin[::-1]
    lut_tt = lut_tt[::-1]
    return lut_tt, lut_fanin_list

def xdata_to_cnf2(data, fanin_list):
    cnf = []
    for idx, x_data_info in enumerate(data): 
        if x_data_info[1] =='':
            continue
        elif x_data_info[1].startswith('0x'):
            no_fanin = len(fanin_list[idx])
            lut_len = int(pow(2, no_fanin))
            lut_tt,_ = lut2tt(x_data_info[1], fanin_list[idx])
            lut_tt = (lut_len-len(lut_tt)) * [0] + lut_tt
            
            # 从LUT中恢复出门电路的真值表 以子句形式加入
            for tt_idx, tt_value in enumerate(lut_tt): 
                if tt_value == 0:
                    tt_bin = bin(tt_idx)[2:]
                    padded_binary_string = tt_bin.zfill(no_fanin)
                    binary_array = [int(bit) for bit in padded_binary_string]
                    tt_array = [-1 if x == 0 else x for x in binary_array]      #[0,1]转换成[-1,1]
                    clause = [x * (y+1) for x, y in zip(tt_array, fanin_list[idx])]
                cnf.append(clause)  
    # cnf = list(set(tuple(x) for x in cnf))
    return cnf

if __name__ == '__main__':
    
    x_data_old, fanin_list_old, fanout_list_old = lut_utils.parse_bench("test/old.bench")   # abc造case时直接生成的
    x_data_new, fanin_list_new, fanout_list_new = lut_utils.parse_bench("test/new.bench")   # main.py生成的
    
    cnf_old = xdata_to_cnf2(x_data_old, fanin_list_old)   
    cnf_new = xdata_to_cnf2(x_data_new, fanin_list_new)   
    
    PI_indexs_old = []
    for i in range(len(x_data_old)):
        if len(fanin_list_old[i]) == 0:
            PI_indexs_old.append(i)        
    PI_indexs_new = []
    for i in range(len(x_data_new)):
        if len(fanin_list_new[i]) == 0:
            PI_indexs_new.append(i)
            
    PO_indexs_old = []
    for i in range(len(x_data_old)):
        if len(fanout_list_old[i]) == 0:
            PO_indexs_old.append(i)  
    assert len(PO_indexs_old) == 1      
    PO_indexs_new = []
    for i in range(len(x_data_new)):
        if len(fanout_list_new[i]) == 0:
            PO_indexs_new.append(i)
    assert len(PO_indexs_new) == 1
    
    po_var_old = PO_indexs_old[0]+1
    po_var_new = PO_indexs_new[0]+1
    
    new_var = max(len(x_data_old),len(x_data_new)) + 1   
    new_clause = [ [-po_var_old,-po_var_new,-new_var], [po_var_old,po_var_new,-new_var],[po_var_old,-po_var_new,new_var],[-po_var_old,po_var_new,new_var],[new_var]]
    cnf = cnf_old + cnf_new + new_clause
    
    sat_status, _ , _ = cnf_utils.kissat_solve( cnf, max(len(x_data_old),len(x_data_new))+1 )
    
    print(sat_status)
    
    

    
    
