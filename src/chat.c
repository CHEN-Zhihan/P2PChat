#include "chat.h"
#include <string.h>
#include "chat_wrapper.h"
#include "parser.h"
int do_user(struct chat_t* chat, char* name) {
    if (chat->state == JOINED_STATE) {
        return JOINED_EXCEPTION;
    }
    chat->name = strdup(name);
    chat->state = NAMED_STATE;
    return SUCCESS;
}

void setup(struct chat_t* chat, char* ip, int server_port, int local_port) {
    memset(chat, 0, sizeof(*chat));
    chat->state = START_STATE;
    chat->ip = get_local_IP();
    chat->local_client =
        setup_network(&chat->manager, ip, chat->ip, server_port, local_port);
    chat->port = local_port;
}

vector_str do_list(struct chat_t* chat) {
    char buffer[BUFFER_SIZE];
    memset(buffer, 0, BUFFER_SIZE);
    sync_request(chat->local_client, "L::\r\n", buffer);
    return parse_do_list(buffer);
}

int do_join(struct chat_t* chat, char* room) {
    if (chat->state == JOINED_STATE) {
        return JOINED_EXCEPTION;
    }
    if (chat->state == START_STATE) {
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
    if (chat->manager.room != nullptr) {
        free(chat->manager.room);
    }
    chat->manager.room = room;

    char* partial_send_msg =
        build_partial_send_msg(room, chat->manager.peer.my_hash_id, chat->name);
    if (chat->manager.peer.partial_send_msg != nullptr) {
        free(chat->manager.peer.partial_send_msg);
    }
    chat->manager.peer.partial_send_msg = partial_send_msg;
    sync_request(chat->local_client, join_msg, buffer);
    setup_keep_alive(&chat->manager, join_msg, chat->local_client);
    vector_str members = parse_join_names(buffer);
    chat->state = JOINED_STATE;
    callback_join(members);
    VECTOR_POINTER_FREE(members);
    return SUCCESS;
}

int do_send(struct chat_t* chat, char* msg) {
    if (chat->state != JOINED_STATE) {
        return UNJOINED_EXCEPTION;
    }
    char* send_msg = malloc(sizeof(*msg) * (strlen(msg) + 3));
    strcpy(send_msg, "T:");
    strcat(send_msg, msg);
    async_request(chat->local_client, send_msg);
    free(send_msg);
    return SUCCESS;
}
