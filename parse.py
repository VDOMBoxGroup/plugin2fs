#!/usr/bin/python
# encoding: utf-8

import sys

if sys.version_info < (2, 7):
    raise Exception("must use python 2.7 or greater")

import argparse
import plugin_parser


def main():
    """Main function
    """
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "src",
        help="path to source XML file",
        type=str
    )
    args_parser.add_argument(
        "dst",
        help="path to destination folder",
        type=str
    )
    args_parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true",
        default=False,
    )

    args = args_parser.parse_args()

    plugin_pr = plugin_parser.create()

    plugin_pr.src = args.src
    plugin_pr.dst = args.dst
    plugin_pr.debug = args.verbose

    plugin_pr.start()


if __name__ == "__main__":
    main()
    sys.exit(0)
