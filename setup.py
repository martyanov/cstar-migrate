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
        'cassandra-driver',
        'future',
        'PyYAML<5.0',
        'arrow',
        'tabulate'
    ],
    keywords='cassandra schema migration',
    entry_points={
        'console_scripts': [
            'cstar-migrate=cstarmigrate.__main__:main',
        ],
    },
)
