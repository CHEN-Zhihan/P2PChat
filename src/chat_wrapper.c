#include <Python.h>
#include <arpa/inet.h>
#include "chat.h"
#include "vector.h"

static struct chat_t chat;

static PyObject* callback = nullptr;
static PyObject* chat_do_user(PyObject* self, PyObject* args);
static PyObject* chat_do_list(PyObject* self, PyObject* args);
static PyObject* chat_set_callback(PyObject* self, PyObject* args);
static PyObject* chat_setup(PyObject* self, PyObject* args);

char* string_list(int);
char* build_tuple(int, char*);
PyObject* to_py_string_list(char**, int);

static PyMethodDef Methods[] = {
    {"do_user", chat_do_user, METH_VARARGS, "this is help message?"},
    {"do_list", chat_do_list, METH_VARARGS, "gg"},
    {"set_callback", chat_set_callback, METH_VARARGS, "this is help message?"},
    {"setup", chat_setup, METH_VARARGS, "gg"},
    {nullptr, nullptr, 0, nullptr}};

static struct PyModuleDef chatDef = {PyModuleDef_HEAD_INIT, "chat", "", -1,
                                     Methods};

PyMODINIT_FUNC PyInit_chat() { return PyModule_Create(&chatDef); }

static PyObject* chat_do_user(PyObject* self, PyObject* args) {
    const char* data;
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

static PyObject* chat_set_callback(PyObject* self, PyObject* args) {
    PyObject* result = nullptr;
    PyObject* temp = nullptr;
    if (PyArg_ParseTuple(args, "O:setCallback", &temp)) {
        if (!PyCallable_Check(temp)) {
            PyErr_SetString(PyExc_TypeError, "parameter must be callable");
            return nullptr;
        }
        Py_XINCREF(temp);
        Py_XDECREF(callback);
        Py_INCREF(Py_None);
        result = Py_None;
    }
    return result;
}

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
