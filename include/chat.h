#ifndef P2PCHAT_H
#define P2PCHAT_H

#include <pthread.h>
#include <stdio.h>
#include "network_manager.h"
#include "vector.h"

enum state_t { START_STATE, NAMED_STATE, JOINED_STATE };

struct chat_t {
    char* name;
    enum state_t state;
    struct network_manager_t manager;
};

int do_user(struct chat_t*, char*);
int do_join(struct chat_t*, char*);
int do_send(struct chat_t*, char*);
vector_str do_list(struct chat_t*);
void do_quit(struct chat_t*);
void setup(struct chat_t*, char*, int, int);

#endif  // P2PCHAT_H
