import sys 
import os 
from main import main as cnf2lut 
from utils.utils import run_command

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('[ERROR] Invalid input')
        print("Usage: python cnf2lut.py <input_cnf> <output_bench>")
    else:
        args = sys.argv[1:]
        input_cnf_path = args[0]
        output_path = args[1]
        
        file_format = output_path.split('.')[-1]
        if file_format == 'bench':
            cnf2lut(input_cnf_path, output_path)
        elif file_format == 'aig' or file_format == 'aiger':
            tmp_bench_path = './tmp.bench'
            cnf2lut(input_cnf_path, tmp_bench_path)
            abc_cmd = 'abc -c \"read_bench {}; write_aiger {};\"'.format(tmp_bench_path, output_path)
            _, _ = run_command(abc_cmd)
            os.remove(tmp_bench_path)
        else:
            print('[ERROR] Unsupported output format')
            print("Support: .bench, .aig, .aiger")
            exit(0)
        
        print('[INFO] Output file is saved at {}'.format(output_path))
            
        