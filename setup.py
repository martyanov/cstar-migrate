import setuptools


VERSION = '0.3.3'


setuptools.setup(
    name='cstar-migrate',
    packages=['cstarmigrate'],
    version=VERSION,
    description='Simple Cassandra database migration tool',
    long_description=open('README.rst').read(),
    url='https://github.com/martyanov/cstar-migrate',
    download_url='https://github.com/martyanov/cstar-migrate/archive/{}.tar.gz'.format(VERSION),
    author='Andrey Martyanov',
    author_email='andrey@martyanov.com',
    license='MIT',
    install_requires=[
        'arrow',
        'cassandra-driver',
        'future',
        'pyyaml<5.0',
        'tabulate',
    ],
    extras_require={
        'dev': [
            'bumpversion==0.5.3',
            'flake8==3.7.9',
            'twine==3.1.1',
        ],
        'test': [
            'pytest-cov==2.8.1',
            'pytest==5.3.5',
            'tox==3.14.5',
        ],
    },
    keywords='cassandra schema migration',
    entry_points={
        'console_scripts': [
            'cstar-migrate=cstarmigrate.__main__:main',
        ],
    },
)
