import numpy as np 
import os 
import random 
import shlex
import subprocess
import time

def read_npz_file(filename):
    data = np.load(filename, allow_pickle=True)
    return data

def run_command(command, timeout=-1):
    try: 
        command_list = shlex.split(command)
        process = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        start_time = time.time()
        while process.poll() is None:
            if timeout > 0 and time.time() - start_time > timeout:
                process.terminate()
                process.wait()
                raise TimeoutError(f"Command '{command}' timed out after {timeout} seconds")

            time.sleep(0.1)

        stdout, stderr = process.communicate()
        stdout = str(stdout).split('\\n')
        return stdout, time.time() - start_time
    except TimeoutError as e:
        return e, -1

def has_common_element(list_a, list_b):
    for a in list_a:
        if a in list_b:
            return True
    return False