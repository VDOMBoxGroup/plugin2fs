#!/bin/bash

if [ -z "$1" -o "$1" = "-h" ]; then
	echo;
	echo "This script unpacks VDOM plugin xml to location where this script stored.";
	echo "Put this script to project's directory for easy update code in working directory.";
	echo;
	echo "usage: unpackxml.sh <plugin_xml_file.xml>";
	echo;

	exit 0;
fi


XMLFILE="$(readlink -m "$1")";

if [ ! -e "${XMLFILE}" ]; then
	echo -e "\nError: File \"${XMLFILE}\" not found. Aborting.\n"
	exit 1;
fi



WORKDIR="$(readlink -m `dirname $0`)";
PLUGIN2FS="${WORKDIR}/../plugin2fs"
TMP="${WORKDIR}/$(basename $0)__tmp";


if [ -d "$TMP" ]; then
	rm -rf "$TMP";
fi


python "${PLUGIN2FS}/parse.py" "${XMLFILE}" "${TMP}";

if [ $? -eq 0 ]; then
	cp -r "${TMP}"/* "${WORKDIR}";
else
	echo -e "\nSomething wrong. Aboring.\n";
	exit 1;
fi


rm -rf "${TMP}";


echo -e "\nComplete.\n";

exit 0;
