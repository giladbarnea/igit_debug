from setuptools import setup, find_packages
import sys

# pip3 install -e .
# or
# [sudo] python3.8 setup.py develop

setup(name='debugtools',
      version='0.0.1',
      description='Inspection decorators, exception handler, formatting tools, a pretty logger, ...',
      author='Gilad Barnea',
      author_email='giladbrn@gmail.com',
      license='MIT',
      packages=find_packages(exclude=["tests?", "*.tests*", "*.tests*.*", "tests*.*", ]),
      install_requires=['more_termcolor>=1.0.9', 'logbook'],
      extras_require=['pytest', 'ipdb', 'IPython'],
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
