#include "network.h"
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
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
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    handle_error(fd, "get server socket failed");
    struct sockaddr_in address = prepare_address(addr, port);
    handle_error(bind(fd, (const struct sockaddr*)&address, sizeof(address)),
                 "bind failed");
    return fd;
}

int get_client_socket(const char* addr, int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    handle_error(fd, "get client socket failed");
    struct sockaddr_in address = prepare_address(addr, port);
    char error_msg[200];
    snprintf(error_msg, 200, "connect to %s:%d failed", addr, port);
    handle_error(connect(fd, (const struct sockaddr*)&address, sizeof(address)),
                 error_msg);
    return fd;
}

void make_non_block(int fd) {
    int flags;
    flags = fcntl(fd, F_GETFL, 0);
    handle_error(flags, "get flag failed");
    flags |= O_NONBLOCK;
    handle_error(fcntl(fd, F_SETFL, flags), "set flag failed");
}
