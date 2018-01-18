#ifndef PARSER_H
#define PARSER_H
#include "message.h"
#include "peer.h"
#include "vector.h"
struct handshake_t {
    struct peer_t peer;
    char* room;
    int msgid;
};

vector_str parse_do_list(char*);
vector_str parse_join_names(char*);
vector_peer_t parse_peers(char*);
int parse_msgid(char*);
struct handshake_t parse_handshake(char*);
struct message_t parse_message(char*);
#endif  // PARSER_H
