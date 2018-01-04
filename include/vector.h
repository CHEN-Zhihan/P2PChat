#ifndef VECTOR_H
#define VECTOR_H

#include <stdio.h>
#include <stdlib.h>
#define USE_VECTOR(type)            \
    typedef struct vector__##type { \
        type* data;                 \
        int size;                   \
        int capacity;               \
    } vector_##type;

#define VECTOR_PUSH_BACK(v, type, element)                                   \
    {                                                                        \
        type t = (element);                                                  \
        if (v.size == v.capacity) {                                          \
            v.data = realloc(v.data, (v.capacity *= 2) * sizeof(*(v.data))); \
        }                                                                    \
        v.data[v.size++] = t;                                                \
    }

#define VECTOR_INIT_CAPACITY(v, type, i)        \
    {                                           \
        int n = (i);                            \
        v.data = malloc(n * sizeof(*(v.data))); \
        if (!v.data) {                          \
            fputs("malloc failed\n", stderr);   \
            abort();                            \
        }                                       \
        v.size = 0;                             \
        v.capacity = n;                         \
    }

#define VECTOR_INIT(v) VECTOR_INIT_CAPACITY(v, i)

#define VECTOR_POP_BACK(v) \
    if (v.size > 0) {      \
        --v.size;          \
    }

#endif  // VECTOR_H
