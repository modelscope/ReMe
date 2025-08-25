import sys

from flowllm.service.base_service import BaseService


def main():
    with BaseService.get_service(*sys.argv[1:]) as service:
        service()


if __name__ == "__main__":
    main()

# python -m build
# twine upload dist/*
