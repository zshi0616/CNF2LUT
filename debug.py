import numpy as np 

class UnionFind:
    def __init__(self, n):
        self.fa = [i for i in range(n)]
        self.len_fa = [0 for i in range(n)]
        self.min = n + 1

    def find(self, x):
        if self.fa[x] != x:
            last = self.fa[x]
            self.fa[x] = self.find(self.fa[x])
            self.len_fa[x] += self.len_fa[last]
        return self.fa[x]

    def merge(self, x, y):
        fa_x = self.find(x)
        fa_y = self.find(y)
        if x != y:
            self.fa[fa_x] = fa_y
            self.len_fa[fa_x] = self.len_fa[fa_y] + 1
        else:
            self.min = min(self.min, self.len_fa[x] + self.len_fa[y] + 1)
            
        self.fa[x] = y
        self.len_fa[x] = 1
        
if __name__ == '__main__':
    uf = UnionFind(5)
    # edge = [[0, 1], [1, 2], [2, 3], [1, 3]]
    # edge = [[0, 1], [1, 2], [2, 3], [3, 1]]
    edge = [[0, 1], [1, 2], [3, 4]]
    for e in edge:
        uf.merge(e[0], e[1])
        print(uf.min)
        
    print()