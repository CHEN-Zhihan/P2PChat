#ifndef MESSAGE_H
#define MESSAGE_H

char* build_join_msg(char*, char*, char*, int);
char* build_list_msg();
char* build_handshake_msg(char*, int);
char* build_partial_handshake_msg(char*, char*, char*, int);
char* build_partial_send_msg(char*, long, char*);
char* build_send_msg(char*, char*);

#endif  // MESSAGE_H
