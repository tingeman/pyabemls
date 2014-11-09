'''
Created on Mar 24, 2012

@author: tin@byg.dtu.dk

Run from command line:

python setup.py sdist
python setup.py bdist_wininst

This will generate a distribution zip file and a windows executable installer
Can be installed by running from the unzipped temporary directory:

python setup.py install

Or from development directory, in development mode - will reflect changes made
in the original development directory instantly automatically.

python setup.py develop
'''

from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        zip_safe=False,
        name="pyabemls",
        version="0.0",
        description="Package for reading ABEM Terrameter LS project files.",
        author="Thomas Ingeman-Nielsen",
        author_email="tin@byg.dtu.dk",
        url="http://???/",
        keywords=["ABEM", "Terrameter LS"],
        classifiers=[
            "Programming Language :: Python",
            "Programming Language :: Python :: 2.7",
            "Development Status :: 3 - Alpha",
            "Operating System :: Microsoft :: Windows",
            "License :: OSI Approved :: GNU General Public License (GPL)",
            "Intended Audience :: Science/Research",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Scientific/Engineering", ],
        packages=find_packages(),
        include_package_data=True,
        package_data={
            # If any package contains *.txt files, include them:
            '': ['*.xml', '*.txt', '*.FOR', '*.for', '*.pyf', '*.pyd']},
        long_description="""\
pyabemls
--------
Package contains class and functions for reading ABEM Terrameter LS project
files (sql files) into a python class for furhter processing.
""")
