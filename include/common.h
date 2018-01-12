#ifndef COMMON_H
#define COMMON_H

#define LAST(str) str[strlen(str) - 1]
#define nullptr NULL

void handle_error(int, const char*);
long hash(char*, char*, char*);
#endif  // COMMON_H
