import sys 
from main import main as cnf2lut 

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('[ERROR] Invalid input')
        print("Usage: python cnf2lut.py <input_cnf> <output_bench>")
    else:
        args = sys.argv[1:]
        input_cnf_path = args[0]
        output_bench_path = args[1]
        cnf2lut(input_cnf_path, output_bench_path)
        