#include "vector.h"
#include <stdio.h>

USE_VECTOR(int);

typedef struct vector_str {
    char** data;
    int size;
    int capacity;
} vector_str;

int main(int argc, const char* argv[]) {
    vector_str s;

    return 0;
}
