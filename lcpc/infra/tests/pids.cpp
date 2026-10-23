#include <bits/stdc++.h>
#include <sys/wait.h>
#include <unistd.h>
int main(){int failed=0;for(int i=0;i<32;i++){pid_t p=fork();if(p==0){usleep(250000);_exit(0);}if(p<0)failed++;}while(wait(nullptr)>0){}if(!failed)return 91;long long a,b;std::cin>>a>>b;std::cout<<a+b<<'\n';}
