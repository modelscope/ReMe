import sys

from flowllm.app import FlowLLMApp

from reme_ai.config.config_parser import ConfigParser


def main():
    with FlowLLMApp(args=sys.argv[1:], parser=ConfigParser) as app:
        app.run_service()

if __name__ == "__main__":
    main()

# python -m build && twine upload dist/*
