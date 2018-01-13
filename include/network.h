#ifndef NETWORK_H
#define NETWORK_H
#include <arpa/inet.h>
#include "common.h"

struct socket_handler_t {
    int fd;
    char buffer[BUFFER_SIZE];
};

int get_client_socket(const char*, int);
int get_server_socket(const char*, int);
int get_socket_port(int);
void make_non_block(int);
char* get_local_IP();
void sync_request(int, char*, char*);
void async_request(int, char*);

#endif  // NETWORK_H
