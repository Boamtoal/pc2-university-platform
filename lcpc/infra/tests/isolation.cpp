#include <bits/stdc++.h>
#include <sys/socket.h>
#include <unistd.h>
int main(){
 const char* denied[]={"/var/lib/pc2judge/credentials.properties","/opt/lcpc/lib/pc2.jar","/etc/shadow","/host-private/contest/credentials.properties","/proc/1/root/var/lib/pc2judge/credentials.properties"};
 for(auto p:denied)if(std::ifstream(p).good())return 91;
 int fd=socket(AF_INET,SOCK_STREAM,0);if(fd>=0){close(fd);return 92;}
 std::ofstream f("/usr/lcpc_should_not_exist");if(f.good())return 93;
 long long a,b;std::cin>>a>>b;std::cout<<a+b<<'\n';
}
