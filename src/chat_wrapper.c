#include <Python.h>
#include "chat.h"

static PyObject* callback = nullptr;
static PyObject* chat_do_user(PyObject* self, PyObject* args);
static PyObject* chat_set_callback(PyObject* self, PyObject* args);

static PyMethodDef Methods[] = {
    {"doUser", chat_do_user, METH_VARARGS, "this is help message?"},
    {"set_callback", chat_set_callback, METH_VARARGS, "this is help message?"},
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
    result = do_user(data);
    return Py_BuildValue("i", result);
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

void observe_add(const char**, )