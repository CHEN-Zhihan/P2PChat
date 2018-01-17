#ifndef PEER_H
#define PEER_H
#include "vector.h"

struct peer_t {
    char* name;
    char* ip;
    int port;
    long hash_id;
};

struct connected_peer_t {
    struct peer_t peer;
    int soc;
    int msgid;
};

USE_STRUCT_VECTOR(peer_t);
USE_STRUCT_VECTOR(connected_peer_t);

void free_peer(struct peer_t p);
void free_connected_peer(struct connected_peer_t*);
struct connected_peer_t get_connected_peer(struct peer_t, int, int);
void free_vector_peer(vector_peer_t peers);

int partition(vector_peer_t* v, int begin, int end);

void sort_peers(vector_peer_t* v, int begin, int end);
#endif  // PEER_H
