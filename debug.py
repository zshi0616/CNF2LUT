import numpy as np
import os 
import glob 
from utils.lut_utils import parse_bench, get_level

def detect_cycle(x_data, fanout_list):
    visited = [0] * len(x_data)
    
    def dfs(node, path):
        visited[node] = 1
        path.append(node)
        
        for v in fanout_list[node]:
            if visited[v] == 0:
                status, path = dfs(v, path)
                if status:
                    return True, path
            elif v in path:
                print('Cycle detected: ')
                line = ''
                for k in path:
                    line += '{}({}) -> '.format(x_data[k][0], k)
                line += '{}({})'.format(x_data[v][0], v)
                print(line)
                print()
                return True, path
        
        path = path[:-1]
        return False, path
        
    for i in range(len(x_data)):
        if visited[i] == 0:
            if i == 5:
                print('debug')
            dfs(i, [])   

if __name__ == '__main__':
    bench_file = './output/tt.bench'
    x_data, fanin_list, fanout_list = parse_bench(bench_file)
    # level_list = get_level(x_data, fanin_list, fanout_list)
    detect_cycle(x_data, fanout_list)
    print()
    
    