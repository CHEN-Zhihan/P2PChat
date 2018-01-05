#include "network.h"
#include <errno.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include "common.h"

struct sockaddr_in prepare_address(const char* addr, int port) {
    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons(port);
    handle_error(inet_pton(AF_INET, addr, &address.sin_addr),
                 "inet_pton failed");
    return address;
}

int get_server_socket(const char* addr, int port) {
    int fd = socket(AF_INET, SOCK_STREAM, SOCK_CLOEXEC);
    handle_error(fd, "socket failed");
    struct sockaddr_in address = prepare_address(addr, port);
    handle_error(bind(fd, (const struct sockaddr*)&address, sizeof(address)),
                 "bind failed");
    handle_error(listen(fd, 10), "listen failed");
    return fd;
}

int get_client_socket(const char* addr, int port) {
    int fd = socket(AF_INET, SOCK_STREAM, SOCK_CLOEXEC);
    handle_error(fd, "socket failed");
    struct sockaddr_in address = prepare_address(addr, port);
    handle_error(connect(fd, (const struct sockaddr*)&address, sizeof(address)),
                 "connect failed");
    return fd;
}
