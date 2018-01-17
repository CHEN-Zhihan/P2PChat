#include "parser.h"
#include <stdlib.h>
#include <string.h>
#include "common.h"
#include "vector.h"

vector_str parse_do_list(char* msg) {
    vector_str result;
    VECTOR_INIT(result);
    if (msg[2] == ':') {
        return result;
    }
    int i = 1;
    while (msg[i + 1] != ':') {
        int j = i;
        while (msg[i + 1] != ':') {
            ++i;
        }
        char* group = malloc(sizeof(*group) * (i - j + 1));
        strncpy(group, msg + i + 1, i - j);
        group[i - j] = '\0';
        VECTOR_PUSH_BACK(result, char*, group);
    }
    return result;
}

vector_str parse_join_names(char* msg) {
    vector_str result;
    VECTOR_INIT(result);
    int i = 3;
    while (msg[i] != ':') {
        while (msg[i] != ':') {
            ++i;
        }
        ++i;
        int j = i;
        while (msg[i] != ':') {
            ++i;
        }
        char* name = strndup(msg + j, i - j);
        VECTOR_PUSH_BACK(result, char*, name);
        ++i;
        while (msg[i] != ':') {
            ++i;
        }
        ++i;
        while (msg[i] != ':') {
            ++i;
        }
        ++i;
    }
    return result;
}

vector_peer_t parse_peers(char* msg) {
    vector_peer_t result;
    VECTOR_INIT(result);
    int i = 2;
    member temp;
    while (msg[i + 1] != ':') {
        while (msg[i] != ':') {
            ++i;
        }
        ++i;
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
        char* port_str = strndup(msg + j, i - j);
        int port;
        sscanf(port_str, "%d", &port);
        temp.hash_id = hash(name, ip, port);
        temp.port = atoi(port);
        free(port);
        VECTOR_PUSH_BACK(result, member, temp);
        ++i;
    }
    return result;
}

int parse_msgid(char* msg) {
    int result;
    sscanf(msg, "S:%d::\r\n", &result);
    return result;
}

struct handshake_t parse_handshake(char* buffer) {
    char username[BUFFER_SIZE];
    char room[BUFFER_SIZE];
    char ip[BUFFER_SIZE];
    struct handshake_t result;
    sscanf(buffer, "P:%s:%s:%s:%d:%d::\r\n", room, username, ip,
           &result.peer.port, &result.msgid);
    result.peer.ip = strdup(ip);
    result.peer.room = strdup(room);
    result.peer.name = strdup(username);
    result.peer.hash_id =
        hash(result.peer.name, result.peer.ip, result.peer.port);
    return result;
}

struct message_t parse_message(char* buffer) {
    struct message_t result;
    int i = 2;
    int j = i;
    while (buffer[i] != ':') {
        ++i;
    }
    result.room = strndup(buffer + j, i - j);
    ++i;
    j = i;
    while (buffer[i] != ':') {
        ++i;
    }
    char* hash_id = strndup(buffer + j, i - j);
    sscanf(hash_id, "%ld", &result.hash_id);
    free(hash_id);
    ++i;
    j = i;
    while (buffer[i] != ':') {
        ++i;
    }
    result.name = strndup(buffer + j, i - j);
    ++i;
    j = i;
    while (buffer[i] != ':') {
        ++i;
    }
    char* msgid = strndup(buffer + j, i - j);
    sscanf(msgid, "%d", &result.msgid);
    free(msgid);
    ++i;
    j = i;
    while (buffer[i] != ':') {
        ++i;
    }
    char* length = strndup(buffer + j, i - j);
    int msglen = 0;
    sscanf(length, "%d", &msglen);
    free(length);
    ++i;
    result.content = strndup(buffer + i, msglen);
    return result;
}
