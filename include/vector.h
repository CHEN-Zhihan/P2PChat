#ifndef VECTOR_H
#define VECTOR_H

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#define USE_VECTOR(type)           \
    typedef struct vector_##type { \
        type* data;                \
        int size;                  \
        int capacity;              \
    } vector_##type;

#define USE_STRUCT_VECTOR(type)    \
    typedef struct vector_##type { \
        struct type* data;         \
        int size;                  \
        int capacity;              \
    } vector_##type;

#define VECTOR_PUSH_BACK(v, type, element)                                   \
    do {                                                                     \
        type t = (element);                                                  \
        if (v.size == v.capacity) {                                          \
            v.data = realloc(v.data, (v.capacity *= 2) * sizeof(*(v.data))); \
        }                                                                    \
        v.data[v.size++] = t;                                                \
    } while (0);

#define VECTOR_STRUCT_PUSH_BACK(v, type, element)                              \
    do {                                                                       \
        struct type __t = (element);                                           \
        if (v.size == v.capacity) {                                            \
            v.data = realloc(v.data, (v.capacity *= 2) * sizeof(struct type)); \
        }                                                                      \
        v.data[v.size++] = __t;                                                \
    } while (0);

#define VECTOR_ERASE(v, i, f)               \
    do {                                    \
        int j = i;                          \
        f(&v.data[j]);                      \
        for (j = i; j != v.size - 1; ++j) { \
            v.data[j] = v.data[j + 1];      \
        }                                   \
        --v.size;                           \
    } while (0);

#define VECTOR_INIT_CAPACITY(v, i)             \
    do {                                       \
        int n = i;                             \
        v.data = calloc(n, sizeof(*(v.data))); \
        if (!v.data) {                         \
            fputs("malloc failed\n", stderr);  \
            abort();                           \
        }                                      \
        v.size = 0;                            \
        v.capacity = n;                        \
    } while (0);

#define VECTOR_INIT(v) VECTOR_INIT_CAPACITY(v, 1)

#define VECTOR_POP_BACK(v) \
    if (v.size > 0) {      \
        --v.size;          \
    }

#define VECTOR_POINTER_POP_BACK(v) \
    if (v.size > 0) {              \
        free(v.data[--v.size]);    \
    }

#define VECTOR_FREE(v) free(v.data)

#define VECTOR_POINTER_FREE(v)          \
    do {                                \
        int i = 0;                      \
        for (i = 0; i != v.size; ++i) { \
            free(v.data[i]);            \
        }                               \
        free(v.data);                   \
    } while (0);

typedef struct vector_str {
    char** data;
    int size;
    int capacity;
} vector_str;

#endif  // VECTOR_H
