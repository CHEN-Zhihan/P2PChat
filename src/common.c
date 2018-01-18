#include "common.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void handle_error(int result, const char* msg) {
    if (result < 0) {
        fprintf(stderr, "[ERROR] %s: %s\n", msg, strerror(errno));
        exit(EXIT_FAILURE);
    }
}

long sdbm_hash(char* str) {
    long hash = 0;
    unsigned int i = 0;
    for (i = 0; i != strlen(str); ++i) {
        hash = str[i] + (hash << 6) + (hash << 16) - hash;
    }
    return hash & 0xFFFFFFFFFFFFFFFF;
}

long hash(char* name, char* ip, int port) {
    char port_str[10];
    snprintf(port_str, 10, "%d", port);
    char* hash_str = malloc(sizeof(*hash_str) *
                            (strlen(port_str) + strlen(ip) + strlen(name) + 1));
    strcpy(hash_str, name);
    strcat(hash_str, ip);
    strcat(hash_str, port_str);
    long result = sdbm_hash(hash_str);
    free(hash_str);
    return result;
}
