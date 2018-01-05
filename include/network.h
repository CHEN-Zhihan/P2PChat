#ifndef NETWORK_H
#define NETWORK_H
#include <arpa/inet.h>

int get_client_socket(const char*, int);
int get_server_socket(const char*, int);
void make_non_block(int);
#endif  // NETWORK_H
