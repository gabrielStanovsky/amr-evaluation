from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="amr_eval",
    version="0.0.1",
    description="Fork of Marco Damonte's AMR evaluation code",
    url="https://github.com/ronentk/amr-evaluation",
    author="Ronen Tamari",
    author_email="ronent@cs.huji.ac.il",
    license="BSD",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[

    ]
)
