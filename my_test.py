from main_exp import *

if __name__ == '__main__':
    cnf_original = [
        [1, 2, -3], [1, -2, 3], [1, -2, -3], 
        [-1, 2, 3], [-1, -2, -3]
    ]
    
    cnf_2 = [
        [1, -2, 3], [1, -2, -3],
        [-1, 2, 3], [-1, -2, -3]
    ]
    
    cnf_4 = [
        [1, 3, 4], [1, -3, -4], 
        [-1, 3, 4], [-1, -3, 4]
    ]
    
    cnf_final = [
        [1, 	-2, 	3], 
        [1, 	-2, 	-3], 
        [-1, 	2, 	3], 
        [-1, 	-2, 	-3], 
        [1, 	-3], 
    ]
    
    cnf = cnf_final
    fanin_var_list = [1, 3]
    fanout_var = 2
    
    tt = subcnf_simulation(cnf, fanin_var_list, fanout_var)
    
    print()
    
    