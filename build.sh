mkdir tmp 

# Install Mockturtle 
cd tools/mockturtle 
mkdir build
cd build
cmake ..
make my_baseline -j4
make my_mapper -j4

# # Install cnf2aig 
# cd ../../cnf2aig
# bash configure && make -j4

