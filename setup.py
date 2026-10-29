import os
import sys
from setuptools import setup, find_packages, Extension

try:
    from Cython.Build import cythonize
    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False

source_ext = ".pyx" if USE_CYTHON else ".cpp"

extra_compile_args = []
extra_link_args = []

if sys.platform != "win32":
    extra_compile_args.extend(["-O3", "-std=c++11"])

pkg_dir = os.path.abspath("tsp_fast_solver")

extensions = [
    Extension(
        name="tsp_fast_solver._tsp_cython",
        sources=[
            os.path.join("tsp_fast_solver", f"_tsp_cython{source_ext}"),
            os.path.join("tsp_fast_solver", "tsp.cpp"),
        ],
        include_dirs=[pkg_dir],
        language="c++",
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    ),
]

if USE_CYTHON:
    ext_modules = cythonize(
        extensions,
        include_path=[pkg_dir, "."],
        compiler_directives={"language_level": "3"},
    )
else:
    ext_modules = extensions

setup(
    packages=find_packages(),
    ext_modules=ext_modules,
    package_data={
        "tsp_fast_solver": ["*.h", "*.pxd", "*.pyx", "*.cpp"],
    },
)
