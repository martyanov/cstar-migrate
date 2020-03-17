import sys

from . import cli


def main():
    cli.main(argv=sys.argv[1:])


if __name__ == '__main__':
    main()
