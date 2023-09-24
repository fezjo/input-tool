from setuptools import setup, find_packages


SCRIPTS = [
    "input_tool/input-generator",
    "input_tool/input-sample",
    "input_tool/input-tester",
]

DESCRIPTION = (
    "Tool which simplifies creating and testing inputs for programming contests."
)

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="input-tool",
    version="1.3.0",
    author="jablkoj (Ján Hozza), fezjo (Jozef Číž)",
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    scripts=SCRIPTS,
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
)
