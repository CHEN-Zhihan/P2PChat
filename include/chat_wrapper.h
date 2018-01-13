#ifndef CHAT_WRAPPER_H
#define CHAT_WRAPPER_H

#include "vector.h"

void callback_add(char*);
void callback_remove(char*);
void callback_join(vector_str);
void callback_msg(char*, char*);

#endif  // CHAT_WRAPPER_H
