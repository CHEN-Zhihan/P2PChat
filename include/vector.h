#ifndef VECTOR_H
#define VECTOR_H

#include <stdio.h>
#include <stdlib.h>
#define VECTOR(type)  \
    struct {          \
        type* data;   \
        int size;     \
        int capacity; \
    }

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
        type n = (i);                           \
        v.data = malloc(n * sizeof(*(v.data))); \
        if (!v.data) {                          \
            fputs("malloc failed\n", stderr);   \
            abort();                            \
        }                                       \
        v.size = 0;                             \
        v.capacity = n;                         \
    }

#define VECTOR_INIT(v) VECTOR_INIT_CAPACITY(v, i)

#define VECTOR_AT(v, i) v.data[i]
#define VECTOR_SIZE(v) v.size
#define VECTOR_POP_BACK(v) \
    if (v.size > 0) {      \
        --v.size;          \
    }

#endif  // VECTOR_H
