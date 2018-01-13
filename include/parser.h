#ifndef PARSER_H
#define PARSER_H
#include "vector.h"

vector_str parse_do_list(char*);
vector_str parse_join_names(char*);
int parse_msgid(char*);

#endif  // PARSER_H
