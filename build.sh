mkdir tmp 

# Install Mockturtle 
cd tools/mockturtle 
mkdir build
cd build
cmake ..
make my_baseline 
make my_mapper 

# # Install cnf2aig 
# cd ../../cnf2aig
# bash configure && make -j4
