import sys

from flowllm.service.base_service import BaseService

from reme_ai.config.config_parser import ConfigParser


def main():
    with BaseService.get_service(*sys.argv[1:], parser=ConfigParser) as service:
        service()


if __name__ == "__main__":
    main()

# python -m build
# twine upload dist/*
