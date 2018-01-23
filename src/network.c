#include "network.h"
#include <errno.h>
#include <fcntl.h>
#include <ifaddrs.h>
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
    handle_error(bind(fd, (struct sockaddr*)&address, sizeof(address)),
                 "bind failed");
    handle_error(listen(fd, 10), "listen failed");
    return fd;
}

int get_server_socket_try_port(const char* addr, int* port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    handle_error(fd, "get server socket failed");
    struct sockaddr_in address = prepare_address(addr, *port);
    while (bind(fd, (struct sockaddr*)&address, sizeof(address)) == -1) {
        *port = (*port + 1) % 65535;
        address = prepare_address(addr, *port);
    }
    handle_error(listen(fd, 10), "listen failed");
    return fd;
}

int get_client_socket(const char* addr, int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    handle_error(fd, "get client socket failed");
    struct sockaddr_in address = prepare_address(addr, port);
    char error_msg[200];
    snprintf(error_msg, 200, "connect to %s:%d failed", addr, port);
    handle_error(connect(fd, (struct sockaddr*)&address, sizeof(address)),
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

char* get_local_IP() {
    struct ifaddrs* ifAddrStruct = nullptr;
    struct ifaddrs* ifa = nullptr;
    void* tmpAddrPtr = nullptr;
    getifaddrs(&ifAddrStruct);
    for (ifa = ifAddrStruct; ifa != nullptr; ifa = ifa->ifa_next) {
        if (!ifa->ifa_addr) {
            continue;
        }
        if (ifa->ifa_addr->sa_family == AF_INET) {  // check it is IP4
            // is a valid IP4 Address
            tmpAddrPtr = &((struct sockaddr_in*)ifa->ifa_addr)->sin_addr;
            char addressBuffer[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, tmpAddrPtr, addressBuffer, INET_ADDRSTRLEN);
            if (strcmp(addressBuffer, "127.0.0.1") != 0) {
                freeifaddrs(ifAddrStruct);
                return strdup(addressBuffer);
            }
        }
    }
    handle_error(-1, "cannot find local address");
    return nullptr;
}

int get_socket_port(int fd) {
    struct sockaddr_in addr;
    socklen_t addrlen;
    handle_error(getsockname(fd, (struct sockaddr*)&addr, &addrlen),
                 "getsockname failed");
    return ntohs(addr.sin_port);
}

void sync_request(int fd, char* send, char* buffer) {
    write(fd, send, strlen(send) + 1);
    read(fd, buffer, BUFFER_SIZE);
}

void async_request(int fd, char* send) { write(fd, send, strlen(send) + 1); }
