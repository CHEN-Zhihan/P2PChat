#include "vector.h"
#include <stdio.h>

int main(int argc, const char* argv) {
    VECTOR(int) v;
    VECTOR_INIT_CAPACITY(v, int, 10);
    int i = 0;
    for (i = 0; i != 200; ++i) {
        VECTOR_PUSH_BACK(v, int, i);
    }
    fprintf(stdout, "%d\t%d\n", VECTOR_AT(v, 1), VECTOR_SIZE(v));
    int a = 0, b = 0;
    return 0;
}
