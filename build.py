#!/usr/bin/python
# encoding: utf-8

import sys

if sys.version_info < (2, 7):
    raise Exception("must use python 2.7 or greater")

import argparse
import plugin_builder


def main():
    """Main function
    """
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "src",
        help="path to source folder",
        type=str
    )
    args_parser.add_argument(
        "dst",
        help="path to destination XML file",
        type=str
    )

    args = args_parser.parse_args()

    plugin_bl = plugin_builder.create()

    plugin_bl.src = args.src
    plugin_bl.dst = args.dst

    plugin_bl.start()


if __name__ == "__main__":
    main()
    sys.exit(0)
