#include "vector.h"
#include <stdio.h>
#include <string.h>
struct peer_t {
    char* name;
    char* ip;
    int port;
    unsigned long hash_id;
    int msgid;
};
USE_STRUCT_VECTOR(peer_t);

unsigned long sdbm_hash(char* str) {
    unsigned long hash = 0;
    unsigned int i = 0;
    for (i = 0; i != strlen(str); ++i) {
        hash = str[i] + (hash << 6) + (hash << 16) - hash;
    }
    return hash & 0xFFFFFFFFFFFFFFFF;
}

unsigned long hash(char* name, char* ip, int port) {
    char port_str[10];
    snprintf(port_str, 10, "%d", port);
    char* hash_str = (char*)malloc(
        sizeof(*hash_str) * (strlen(port_str) + strlen(ip) + strlen(name) + 1));
    strcpy(hash_str, name);
    strcat(hash_str, ip);
    strcat(hash_str, port_str);
    unsigned long result = sdbm_hash(hash_str);
    free(hash_str);
    return result;
}

vector_peer_t parse_peers(char* msg) {
    vector_peer_t result;
    VECTOR_INIT(result);
    int i = 2;
    struct peer_t temp;
    while (msg[i] != ':') {
        ++i;
    }
    ++i;
    while (msg[i] != ':') {
        int j = i;
        while (msg[i] != ':') {
            ++i;
        }
        char* name = strndup(msg + j, i - j);
        temp.name = name;
        ++i;
        j = i;
        while (msg[i] != ':') {
            ++i;
        }
        char* ip = strndup(msg + j, i - j);
        temp.ip = ip;
        ++i;
        j = i;
        while (msg[i] != ':') {
            ++i;
        }
        temp.msgid = 0;
        char* port_str = strndup(msg + j, i - j);
        sscanf(port_str, "%d", &temp.port);
        temp.hash_id = hash(name, ip, temp.port);
        fprintf(stderr, "[DEBUG] parse members: %s %s %d %lu\n", name, ip,
                temp.port, temp.hash_id);
        free(port_str);
        VECTOR_STRUCT_PUSH_BACK(result, peer_t, temp);
        ++i;
    }
    return result;
}

int main(int argc, const char* argv[]) {
    vector_peer_t p1 = parse_peers(
        "M:12917793433669227309:2:147.8.211.46:6666:1:147.8.211.46:5555::\r\n");
    vector_peer_t p2 = parse_peers(
        "M:12917793433669227309:2:147.8.211.46:6666:1:147.8.211.46:5555::\r\n");
    return 0;
}
