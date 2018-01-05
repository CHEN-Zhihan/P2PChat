#include "common.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

inline void handle_error(int result, const char* msg) {
    if (result < 0) {
        fprintf(stderr, "[ERROR] %s: %s\n", msg, strerror(errno));
        exit(EXIT_FAILURE);
    }
}
