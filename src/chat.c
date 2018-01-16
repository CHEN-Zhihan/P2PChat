#include "chat.h"

int do_user(struct chat_t* chat, char* name) {
    if (chat->state == JOINED_STATE) {
        return JOINED_EXCEPTION;
    }
    chat->name = strdup(name);
    chat->state = NAMED_EXCEPTION;
    return SUCCESS;
}

void setup(struct chat_t* chat, char* ip, int server_port, int local_port) {
    memset(chat, 0, sizeof(*chat));
    chat->current_state = START_STATE;
    chat->ip = get_local_IP();
    chat->local_client =
        setup_network(&chat->manager, ip, chat->ip, server_port, local_port);
    chat->port = local_port;
}

vector_str do_list(struct chat_t* chat) {
    char buffer[BUFFER_SIZE];
    sync_request(chat->local_client, build_list_msg(), buffer);
    return parse_do_list(buffer);
}

vector_str do_join(struct chat_t* chat, char* room) {
    if (chat->current_state == JOINED_STATE) {
        return JOINED_EXCEPTION;
    }
    if (chat->current_state == START_STATE) {
        return UNNAMED_EXCEPTION;
    }
    char buffer[BUFFER_SIZE];
    char* join_msg = build_join_msg(room, chat->name, chat->ip, chat->port);
    chat->manager.peer.my_hash_id = hash(chat->name, chat->ip, chat->port);
    char* partial_handshake_msg =
        build_partial_handshake_msg(room, chat->name, chat->ip, chat->port);
    if (chat->manager.peer.partial_handshake_msg != nullptr) {
        free(chat->manager.peer.partial_handshake_msg);
    }
    chat->manager.peer.partial_handshake_msg = partial_handshake_msg;
    sync_request(chat->local_client, join_msg, buffer);
    setup_keep_alive(&chat->manager, join_msg, chat->local_client);
    vector_str members = parse_join_names(buffer);
    return members;
}
