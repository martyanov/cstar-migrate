import setuptools


VERSION = '0.4.0a2'


setuptools.setup(
    name='cstar-migrate',
    packages=setuptools.find_packages(),
    version=VERSION,
    description='Cassandra schema migration tool',
    long_description=open('README.rst').read(),
    long_description_content_type='text/x-rst',
    url='https://github.com/martyanov/cstar-migrate',
    download_url=f'https://github.com/martyanov/cstar-migrate/archive/{VERSION}.tar.gz',
    author='Andrey Martyanov',
    author_email='andrey@martyanov.com',
    license='MIT',
    license_file='LICENSE',
    python_requires='>=3.7,<4.0',
    install_requires=[
        'arrow<0.16',
        'cassandra-driver<4.0',
        'pyyaml<5.0',
        'tabulate<0.9',
    ],
    extras_require={
        'dev': [
            'flake8==3.7.9',
            'twine==3.1.1',
        ],
        'test': [
            'pytest-cov==2.8.1',
            'pytest==5.3.5',
            'tox==3.14.5',
        ],
    },
    entry_points={
        'console_scripts': [
            'cstar-migrate=cstarmigrate.__main__:main',
        ],
    },
    keywords='cassandra schema migration tool',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Database',
    ],
    project_urls={
        'Bug Reports': 'https://github.com/martyanov/cstar-migrate/issues',
        'Repository': 'https://github.com/martyanov/cstar-migrate',
    },
)
