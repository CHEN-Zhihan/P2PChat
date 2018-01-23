#include "peer.h"
#include <string.h>
#include <unistd.h>
void free_peer(struct peer_t p) {
    free(p.name);
    free(p.ip);
}

void free_connected_peer(struct connected_peer_t* p) {
    close(p->soc);
    free_peer(p->peer);
    p->soc = 0;
}

void free_vector_peer(vector_peer_t peers) {
    int i = 0;
    for (i = 0; i != peers.size; ++i) {
        free_peer(peers.data[i]);
    }
    free(peers.data);
}

int partition(vector_peer_t* v, int begin, int end) {
    int i = begin - 1, j = begin;
    struct peer_t pivot = v->data[end - 1];
    for (j = begin; j != end - 1; ++j) {
        if (v->data[j].hash_id < pivot.hash_id) {
            struct peer_t temp = v->data[j];
            v->data[j] = v->data[i + 1];
            v->data[++i] = temp;
        }
    }
    struct peer_t temp = v->data[i + 1];
    v->data[i + 1] = pivot;
    v->data[end - 1] = temp;
    return i + 1;
}

void sort_peers(vector_peer_t* v, int begin, int end) {
    if (begin >= end - 1) {
        return;
    }
    int mid = partition(v, begin, end);
    sort_peers(v, begin, mid);
    sort_peers(v, mid + 1, end);
}

struct connected_peer_t get_connected_peer(struct peer_t p, int soc,
                                           int msgid) {
    struct connected_peer_t result;
    result.soc = soc;
    result.peer.msgid = msgid;
    result.peer.hash_id = p.hash_id;
    result.peer.ip = strdup(p.ip);
    result.peer.name = strdup(p.name);
    result.peer.port = p.port;
    return result;
}

struct peer_t* find_peer(vector_peer_t peers, unsigned long hash_id) {
    int i = 0;
    for (i = 0; i != peers.size; ++i) {
        if (peers.data[i].hash_id == hash_id) {
            return &peers.data[i];
        }
    }
    return nullptr;
}
