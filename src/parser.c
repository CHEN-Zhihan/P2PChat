#include <string.h>
#include <stdlib.h>
#include "parser.h"
#include "vector.h"
#include "common.h"

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
