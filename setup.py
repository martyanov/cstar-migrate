import setuptools


def _get_long_description():
    with open('README.rst') as readme_file:
        return readme_file.read()


setuptools.setup(
    name='cstar-migrate',
    use_scm_version=True,
    packages=setuptools.find_packages(),
    description='Cassandra schema migration tool',
    long_description=_get_long_description(),
    long_description_content_type='text/x-rst',
    url='https://github.com/martyanov/cstar-migrate',
    author='Andrey Martyanov',
    author_email='andrey@martyanov.com',
    license='MIT',
    license_file='LICENSE',
    keywords='cassandra schema migration tool',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Database',
    ],
    project_urls={
        'Bug Reports': 'https://github.com/martyanov/cstar-migrate/issues',
        'Repository': 'https://github.com/martyanov/cstar-migrate',
    },
    python_requires='>=3.8,<4',
    setup_requires=[
        'setuptools_scm==3.3.3',
    ],
    install_requires=[
        'arrow>=0.15,<2',
        'cassandra-driver>=3.0,<4',
        'pyyaml>=5.1,<7',
        'tabulate>=0.8,<0.10',
    ],
    extras_require={
        'dev': [
            'flake8==6.1.0',
            'twine==4.0.2',
        ],
        'test': [
            'pytest-cov==4.1.0',
            'pytest==7.4.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'cstar-migrate=cstarmigrate.__main__:main',
        ],
    },
)
