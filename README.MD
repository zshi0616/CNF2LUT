# CNF2LUT: Circuit-based Reformulation of Conjunctive Normal Form

Official code repository for the paper: 
[**CNF2LUT**] (https://) (Under Review)

Authors: Anonymous Author


## Abstract 
TODO

## Run
Firstly, you need to create two directories within your project directory:

    case/ - Put all the CNF files that need to be converted into this directory.

    output/ - The converted files will be saved in this directory.

Run the following command:
```sh 
python main.py
```

## Create Cases
We can use [abc](https://github.com/berkeley-abc/abc) and tool to create original circuit
```sh 
abc -c "read_truth 12; strash; write_bench tmp/old.bench; write_aiger tmp/old.aig"
```

Then, we use the aigtocnf tool to convert circuit to CNF. The tool can be find in `tools/aiger`

```sh
# Compile aiger tools (if need)
cd tools/aiger
bash ./configure.sh && make 
cd ../../

./tools/aiger/aigtocnf ./tmp/old.aig ./tmp/old.cnf
```
