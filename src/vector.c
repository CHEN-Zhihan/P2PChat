#include "vector.h"

void free_vector_member(vector_member m) {
    int i = 0;
    for (i = 0; i != m.size; ++i) {
        free(m.data[i].name);
        free(m.data[i].ip);
    }
    free(m.data);
}

int partition(vector_member* v, int begin, int end) {
    int i = begin - 1, j = begin;
    member pivot = v->data[end - 1];
    for (j = begin; j != end - 1; ++j) {
        if (v->data[j].hash_id < pivot.hash_id) {
            member temp = v->data[j];
            v->data[j] = v->data[i + 1];
            v->data[++i] = temp;
        }
    }
    member temp = v->data[i + 1];
    v->data[i + 1] = pivot;
    v->data[end - 1] = temp;
    return i + 1;
}

void sort_members(vector_member* v, int begin, int end) {
    if (begin >= end - 1) {
        return;
    }
    int mid = partition(v, begin, end);
    sort_members(v, begin, mid);
    sort_members(v, mid + 1, end);
}
