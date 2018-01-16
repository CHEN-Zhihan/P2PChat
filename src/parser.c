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
        char* port = strndup(msg + j, i - j);

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
