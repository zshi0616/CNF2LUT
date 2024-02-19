import utils.aiger_utils as aiger_utils
import utils.circuit_utils as circuit_utils

if __name__ == '__main__':
    aig_path = './tmp/output.aig'
    x_data, edge_index = aiger_utils.aig_to_xdata(aig_path)
    fanin_list, fanout_list = circuit_utils.get_fanin_fanout(x_data, edge_index)
    PO_indexs = []
    PI_indexs = []
    for i in range(len(x_data)):
        if len(fanout_list[i]) == 0 and len(fanin_list[i]) > 0:
            PO_indexs.append(i)
        if len(fanin_list[i]) == 0 and len(fanout_list[i]) > 0:
            PI_indexs.append(i)
    assert len(PO_indexs) == 1
    
    print()