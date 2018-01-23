#ifndef MESSAGE_H
#define MESSAGE_H

struct message_t {
    unsigned long hash_id;
    char* room;
    char* name;
    char* content;
    int msgid;
};

char* build_join_msg(char*, char*, char*, int);
char* build_list_msg();
char* build_handshake_msg(char*, int);
char* build_partial_handshake_msg(char*, char*, char*, int);
char* build_partial_send_msg(char*, unsigned long, char*);
char* build_send_msg(char*, int, char*);
void free_message(struct message_t);
#endif  // MESSAGE_H
