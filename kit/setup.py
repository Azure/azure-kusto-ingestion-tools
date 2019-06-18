from setuptools import setup, find_packages

setup(
    name="azure-kusto-ingestion-tools",
    version="0.3.0",
    long_description=open("README.md", "r").read(),
    long_description_content_type='text/markdown',
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
        "azure-kusto-ingest>=0.0.31",
        "azure-kusto-data>=0.0.31",
        "azure-storage",
        # TODO: this should be optional, because it is just an attempt to save effort and installation takes a while
        # "azure-cli",
        "typing-inspect",
        "ijson",
        "dacite",
        "adal",
        "click",
        "maya",
        "pyarrow",
        "pytest",
        "sqlparse"
    ]
)
