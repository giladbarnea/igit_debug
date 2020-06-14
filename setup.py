from setuptools import setup, find_packages
import sys

# pip3 install -e .
# or
# [sudo] python3.8 setup.py develop
with open("README.md", "r") as fh:
    long_description = fh.read()
setup(name='igit_debug',
      version='0.0.2',
      description='Inspection decorators, exception handler, formatting tools, a pretty logger, ...',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='Gilad Barnea',
      author_email='giladbrn@gmail.com',
      license='MIT',
      packages=find_packages(exclude=["tests?", "*.tests*", "*.tests*.*", "tests*.*", ]),
      install_requires=['more_termcolor>=1.0.9', 'logbook'],
      extras_require={'dev': ['pytest', 'ipdb', 'IPython', 'semver', 'twine']},
      classifiers=[
          # https://pypi.org/classifiers/
          'Development Status :: 1 - Planning',
          'Intended Audience :: Developers',
          "License :: OSI Approved :: MIT License",
          'Operating System :: OS Independent',
          "Programming Language :: Python :: 3 :: Only",
          'Topic :: Software Development :: Debuggers',
          ]
      )
