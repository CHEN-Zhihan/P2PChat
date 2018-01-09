#include "parser.h"
#include <stdlib.h>
#include <string.h>
#include "common.h"
#include "vector.h"

vector_str parse_do_list(char* msg) {
    vector_str result;
    VECTOR_INIT_CAPACITY(result, char*, 1);
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

vector_member parse_member(char* msg) {
    vector_member result;
    VECTOR_INIT_CAPACITY(result, member, 1);
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
        temp.port = atoi(port);
        free(port);
        VECTOR_PUSH_BACK(result, member, temp);
        ++i;
    }
    return result;
}
