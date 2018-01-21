from setuptools import setup, Extension

sources = ["cpython.c"]

apitest = Extension("apitest", sources=sources)
setup(name="apitest", version="1.0", description="test", ext_modules=[apitest])
