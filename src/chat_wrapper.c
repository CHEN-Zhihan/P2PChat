#include <Python.h>
#include "chat.h"

static PyObject* chat_print(PyObject* self, PyObject* args);
static PyMethodDef Methods[] = {
    {"print", chat_print, METH_VARARGS, "this is help message?"},
    {nullptr, nullptr, 0, nullptr}};

static struct PyModuleDef chatDef = {PyModuleDef_HEAD_INIT, "chat", "", -1,
                                     Methods};

PyMODINIT_FUNC PyInit_chat() { return PyModule_Create(&chatDef); }

static PyObject* chat_print(PyObject* self, PyObject* args) {
    const char* data;
    int result;
    if (!PyArg_ParseTuple(args, "s", &data)) {
        return nullptr;
    }
    result = print(data);
    return Py_BuildValue("i", result);
}
