import setuptools


VERSION = '0.4.0a1'


setuptools.setup(
    name='cstar-migrate',
    packages=['cstarmigrate'],
    version=VERSION,
    description='Cassandra schema migration tool',
    long_description=open('README.rst').read(),
    url='https://github.com/martyanov/cstar-migrate',
    download_url='https://github.com/martyanov/cstar-migrate/archive/{}.tar.gz'.format(VERSION),
    author='Andrey Martyanov',
    author_email='andrey@martyanov.com',
    license='MIT',
    python_requires='>=3.7,<4.0',
    install_requires=[
        'arrow<0.16',
        'cassandra-driver<4.0',
        'pyyaml<5.0',
        'tabulate<0.9',
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
