#include "chat.h"
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "server.h"

chat_t chat;

void set_address(char* serv_addr, int serv_port, int port) {
    set_server_address(serv_addr, serv_port, port);
}

int do_user(const char* s) {
    if (chat.current_state == JOINED_STATE) {
        return JOINED_EXCEPTION;
    }
    chat.name = s;
    chat.current_state = NAMED_STATE;
    return SUCCESS;
}

vector_str do_list() {
    if (!connected()) {
        setup_server();
    }
    vector_str result = request_do_list();
    return result;
}
