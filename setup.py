from setuptools import find_packages, setup

setup(
    name="pytest-apireport",
    version="0.1.0",
    author="Kim Gustyr",
    author_email="khvn26@gmail.com",
    entry_points={"pytest11": ["name_of_plugin = pytest_apireport.plugin"]},
    packages=find_packages(
        include=["*"],
        exclude=["tests*"],
    ),
    python_requires=">=3.8.1",
    install_requires=[
        "pytest",
        "pydantic",
        "requests",
    ],
    extras_require={
        "test": ["pytest-httpserver", "hypothesis", "pytest-xdist", "werkzeug"],
    },
)
