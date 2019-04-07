import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    author="melkor",
    author_email="hohav@fastmail.com",
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    description="Parsing library for SSBM replay files",
    install_requires=['py-ubjson'],
    long_description=long_description,
    long_description_content_type="text/x-rst",
    name="py-slippi",
    packages=setuptools.find_packages(),
    python_requires='~=3.6',
    url="https://github.com/hohav/py-slippi",
    version="1.2.0",
)
