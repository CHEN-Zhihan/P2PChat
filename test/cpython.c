#include <Python.h>
#include <assert.h>
static PyObject* callback = NULL;
static PyObject* apitest_set_callback(PyObject*, PyObject*);
void callback_test();
static int xxx = 1;
static PyMethodDef Methods[] = {
    {"set_callback", apitest_set_callback, METH_VARARGS, "no help"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef test_def = {PyModuleDef_HEAD_INIT, "apitest", "", -1,
                                      Methods};

PyMODINIT_FUNC PyInit_apitest() { return PyModule_Create(&test_def); }

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
    PyObject* python_result = PyObject_Call(callback, args, NULL);
    Py_DECREF(args);
    if (python_result == NULL) {
        fprintf(stderr, "[ERROR] callback tuple failed");
        exit(EXIT_FAILURE);
    }
    Py_DECREF(python_result);
}

void callback_string(char* str, int flag) {
    PyObject* result = PyUnicode_FromString(str);
    callback_tuple(flag, result);
}
void callback_add(char* name) {
    fprintf(stderr, "callback add!!\n");
    callback_string(name, 1);
}

static PyObject* apitest_set_callback(PyObject* self, PyObject* args) {
    PyObject* result = NULL;
    PyObject* temp = NULL;
    if (PyArg_ParseTuple(args, "O:set_callback", &temp)) {
        if (!PyCallable_Check(temp)) {
            PyErr_SetString(PyExc_TypeError, "parameter must be callable");
            return NULL;
        }
        Py_XINCREF(temp);
        Py_XDECREF(callback);
        callback = temp;
        Py_INCREF(Py_None);
        ++xxx;
        char* str = malloc(sizeof(char) * 5);
        str[0] = '6';
        str[1] = '5';
        str[2] = '\0';
        callback_add(str);
        callback_add(str);
        result = Py_None;
    }
    return result;
}
