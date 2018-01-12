#include "peer.h"
#include <stdlib.h>
char* build_handshake_msg(int, char*);

bool is_backward(vector_peer backwards, long hash_id) {
    int i = 0;
    for (i = 0; i != backwards.size; ++i) {
        if (backwards.data[i].hash_id == hash_id) {
            return true;
        }
    }
    return false;
}

int handshake(struct server_t* server, int peer_soc, char* partial_msg) {
    char* handshake_msg = build_handshake_msg(server->last_msg, partial_msg);
}

char* build_handshake_msg(int last_msg, char* partial_msg) {
    char last_msg_str[10];
    sprintf(last_msg_str, "%d", last_msg);
    size_t size = sizeof(char) * (strlen(partial_msg) + 1 +
                                  strlen(last_msg_str) + strlen("::\r\n") + 1);
    char* result = malloc(size);
    strcpy(result, partial_msg);
    strcat(result, ":");
    strcat(result, last_msg_str);
    strcat(result, "::\r\n");
    return result;
}
