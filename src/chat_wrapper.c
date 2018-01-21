#include <Python.h>
#include <arpa/inet.h>
#include <pthread.h>
#include "chat.h"
#include "vector.h"

static struct chat_t chat;
static pthread_mutex_t mutex;
static PyObject* callback = nullptr;
static PyObject* chat_do_user(PyObject* self, PyObject* args);
static PyObject* chat_do_list(PyObject* self, PyObject* args);
static PyObject* chat_set_callback(PyObject* self, PyObject* args);
static PyObject* chat_setup(PyObject* self, PyObject* args);
static PyObject* chat_do_join(PyObject* self, PyObject* args);

char* string_list(int);
PyObject* to_py_string_list(char**, int);

static PyMethodDef Methods[] = {
    {"do_user", chat_do_user, METH_VARARGS, "this is help message?"},
    {"do_list", chat_do_list, METH_VARARGS, "gg"},
    {"set_callback", chat_set_callback, METH_VARARGS, "gg"},
    {"do_join", chat_do_join, METH_VARARGS, "no help"},
    {"setup", chat_setup, METH_VARARGS, "gg"},
    {nullptr, nullptr, 0, nullptr}};

static struct PyModuleDef chatDef = {PyModuleDef_HEAD_INIT, "chat", "", -1,
                                     Methods};

PyMODINIT_FUNC PyInit_chat() { return PyModule_Create(&chatDef); }

static PyObject* chat_do_user(PyObject* self, PyObject* args) {
    char* data;
    int result;
    if (!PyArg_ParseTuple(args, "s", &data)) {
        return nullptr;
    }
    result = do_user(&chat, data);
    return Py_BuildValue("i", result);
}

static PyObject* chat_setup(PyObject* self, PyObject* args) {
    char* address;
    int server_port, port;
    if (!PyArg_ParseTuple(args, "sii", &address, &server_port, &port)) {
        return nullptr;
    }
    setup(&chat, address, server_port, port);
    return Py_None;
}

static PyObject* chat_do_list(PyObject* self, PyObject* args) {
    vector_str list = do_list(&chat);
    PyObject* result = to_py_string_list(list.data, list.size);
    VECTOR_POINTER_FREE(list);
    return result;
}

static PyObject* chat_do_join(PyObject* self, PyObject* args) {
    char* room;
    int result;
    if (!PyArg_ParseTuple(args, "s", &room)) {
        return nullptr;
    }
    result = do_join(&chat, room);
    return Py_BuildValue("i", result);
}

static PyObject* chat_set_callback(PyObject* self, PyObject* args) {
    pthread_mutex_init(&mutex, nullptr);
    PyObject* result = nullptr;
    PyObject* temp = nullptr;
    if (PyArg_ParseTuple(args, "O:setCallback", &temp)) {
        if (!PyCallable_Check(temp)) {
            PyErr_SetString(PyExc_TypeError, "parameter must be callable");
            return nullptr;
        }
        Py_XINCREF(temp);
        Py_XDECREF(callback);
        callback = temp;
        Py_INCREF(Py_None);
        result = Py_None;
    }
    return result;
}

void setup_python_threads() { PyEval_InitThreads(); }

PyObject* to_py_string_list(char** list, int s) {
    PyObject* result = PyList_New(s);
    if (!result) {
        return nullptr;
    }
    int i = 0;
    for (i = 0; i != s; ++i) {
        PyObject* unicode = PyUnicode_FromString(list[i]);
        PyList_SetItem(result, i, unicode);
    }
    return result;
}

PyObject* build_observe_tuple(int flag, PyObject* o) {
    PyObject* result = PyTuple_New(2);
    PyObject* f = PyLong_FromLong(flag);
    PyTuple_SetItem(result, 0, f);
    PyTuple_SetItem(result, 1, o);
    return result;
}

void callback_tuple(int flag, PyObject* o) {
    PyObject* tuple = build_observe_tuple(flag, o);
    PyObject* args = PyTuple_New(1);
    PyTuple_SetItem(args, 0, tuple);
    PyObject* python_result = PyObject_Call(callback, args, nullptr);
    Py_DECREF(args);
    if (python_result == nullptr) {
        fprintf(stderr, "[ERROR] callback tuple failed");
        exit(EXIT_FAILURE);
    }
    Py_DECREF(python_result);
}

void callback_string(char* str, int flag) {
    PyGILState_STATE state;
    state = PyGILState_Ensure();
    PyObject* result = PyUnicode_FromString(str);
    callback_tuple(flag, result);
    PyGILState_Release(state);
}

void callback_remove(char* name) { callback_string(name, OBSERVE_REMOVE); }

void callback_add(char* name) { callback_string(name, OBSERVE_ADD); }

void callback_msg(char* name, char* msg) {
    PyGILState_STATE state;
    state = PyGILState_Ensure();
    PyObject* tuple = PyTuple_New(2);
    PyObject* sender = PyUnicode_FromString(name);
    PyObject* message = PyUnicode_FromString(msg);
    PyTuple_SetItem(tuple, 0, sender);
    PyTuple_SetItem(tuple, 1, message);
    callback_tuple(OBSERVE_MESSAGE, tuple);
    PyGILState_Release(state);
}

void callback_join(vector_str names) {
    int i = 0;
    for (i = 0; i != names.size; ++i) {
        fprintf(stderr, "[DEBUG] %s\n", names.data[i]);
    }
    PyObject* objects = to_py_string_list(names.data, names.size);
    callback_tuple(OBSERVE_JOIN, objects);
}
