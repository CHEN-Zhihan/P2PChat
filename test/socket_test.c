#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

struct sockaddr_in prepare_address(const char* addr, int port) {
    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons(port);
    inet_pton(AF_INET, addr, &address.sin_addr);
    return address;
}

int get_server_socket(const char* addr, int* port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address = prepare_address(addr, *port);
    while (bind(fd, (struct sockaddr*)&address, sizeof(address)) == -1) {
        *port = (*port + 1) % 65535;
        address = prepare_address(addr, *port);
    }
    listen(fd, 10);
    return fd;
}

int get_client_socket(const char* addr, int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address = prepare_address(addr, port);
    char error_msg[200];
    snprintf(error_msg, 200, "connect to %s:%d failed", addr, port);
    connect(fd, (struct sockaddr*)&address, sizeof(address));
    return fd;
}

int get_socket_port(int fd) {
    struct sockaddr_in addr;
    socklen_t addrlen;
    if (getsockname(fd, (struct sockaddr*)&addr, &addrlen) == -1) {
        fprintf(stderr, "[ERROR] %s\n", strerror(errno));
    }
    return ntohs(addr.sin_port);
}

void* listener(void* p) {
    int fd = *(int*)p;
    int pp = get_socket_port(fd);
    fprintf(stderr, "waiting at %d\n", pp);
    int result = accept(fd, NULL, NULL);
    fprintf(stderr, "ggggggggggggggggggg\n");
    return NULL;
}

int main(int argc, const char* argv[]) {
    char ip[] = "127.0.0.1";
    int port = 6666;
    int server = get_server_socket(ip, &port);
    fprintf(stderr, "sending to %d\n", port);
    pthread_t l;
    pthread_create(&l, NULL, &listener, (void*)&server);
    sleep(10);
    fprintf(stderr, "wake up\n");
    int client = get_client_socket(ip, port);
    fprintf(stderr, "before join");
    pthread_join(l, NULL);
    return 0;
}
