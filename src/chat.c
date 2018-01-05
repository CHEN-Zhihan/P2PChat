#include "chat.h"
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "parser.h"
#include "local_server.h"

void setup(struct chat_t* chat, char* serv_addr, int serv_port, int port) {
    chat->local_soc = setup_local_server(&chat->server, port);
    connect_to_server(&chat->server, serv_addr, serv_port);
}

int do_user(struct chat_t* chat, const char* s) {
    if (chat->current_state == JOINED_STATE) {
        return JOINED_EXCEPTION;
    }
    chat->name = s;
    chat->current_state = NAMED_STATE;
    return SUCCESS;
}

vector_str do_list(struct chat_t* chat) {
    transit(chat->local_soc, "L::\r\r", chat->local_buffer);
    vector_str result = parse_do_list(chat->local_buffer);
    return result;
}
