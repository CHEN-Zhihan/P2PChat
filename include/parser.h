#ifndef PARSER_H
#define PARSER_H
#include "peer.h"
#include "vector.h"

vector_str parse_do_list(char*);
vector_str parse_join_names(char*);
vector_peer_t parse_peers(char*);
int parse_msgid(char*);

#endif  // PARSER_H
