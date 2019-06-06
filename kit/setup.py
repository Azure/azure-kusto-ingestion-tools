from setuptools import setup, find_packages

setup(
    name="azure-kusto-ingestion-tools",
    version="0.1.0",
    description="Kusto Ingestion Tools (Kit)",
    url="https://github.com/Azure/azure-kusto-ingestion-tools",
    author="Microsoft Corporation",
    author_email="kustalk@microsoft.com",
    packages=find_packages(exclude=["azure", "tests"]),
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="kusto wrapper client library",
    entry_points="""
        [console_scripts]
        kit=kit.cli:main
    """,
    install_requires=[
        "azure-kusto-ingest>=0.0.30",
        "azure-kusto-data>=0.0.30",
        "azure-storage",
        # TODO: this should be optional, because it is just an attempt to save effort and installation takes a while
        # "azure-cli",
        "typing-inspect",
        "adal",
        "click",
        "maya",
        "pyarrow",
        "pytest",
        "sqlparse"
    ]
)
