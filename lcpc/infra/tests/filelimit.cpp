#include <bits/stdc++.h>
int main(){std::ofstream f("large.bin",std::ios::binary);std::string s(65536,'x');for(int i=0;i<40;i++)f<<s;std::cout<<"unexpected\n";}
