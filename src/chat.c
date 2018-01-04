#include "chat.h"
#include <string.h>

chat_t chat;

int do_user(const char* s) {
    if (chat.current_state == JOINED_STATE) {
        return JOINED_EXCEPTION;
    }
    chat.name = s;
    chat.current_state = NAMED_STATE;
    return SUCCESS;
}

vector_str do_list() {
    vector_str result;
    VECTOR_INIT_CAPACITY(result, char*, 10);
    VECTOR_PUSH_BACK(result, char*, "what the fuck");
    return result;
}
