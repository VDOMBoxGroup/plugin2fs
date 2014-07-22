#!/usr/bin/python
# encoding: utf-8

import base64
import cgi
import collections
import cStringIO
import json
import os
import sys
import xml

from uuid import uuid4 as uuid

__version__ = "0.0.1"


INFO_JSON = "__info__.json"
EVENTS_JSON = "custom_events.json"
PLUGIN_ICON = "plugin.icon"
TIMERS_JSON = "timers.json"


RESERVED_NAMES = (
    INFO_JSON,
    EVENTS_JSON,
    PLUGIN_ICON,
    TIMERS_JSON,
)


def check_data(data):
    return '"' in data or \
           "'" in data or \
           "<" in data or \
           ">" in data or \
           "\n" in data or \
           "&" in data


def cdata(data, force=False):
    # remove return after application fixes
    return data
    
    if not data.strip() and not force:
        return data

    if force or check_data(data):
        data = data.replace("]]>", "]]]]><![CDATA[")
        return "<![CDATA[{}]]>".format(data)

    return data


def clear_data(data):
    if len(set(data) - set(["\n", "\t"])) > 0:
        return data
    else:
        return ""


class Builder(object):

    __instance = None

    def __new__(cls, *a, **kwa):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def initialize(
        self,
        src="",
        dst="",
        debug=False,
        library="",
        library_copy_mode=""
    ):

        self.debug = debug
        self.src = src
        self.dst = dst
        self.library = library
        self.library_copy_mode = library_copy_mode
        self.output = None
        return self

    def start(self):
        """Setup logging and start main process
        """
        self.dst = self.dst or os.path.basename(os.path.normpath(self.src))

        if not os.path.isdir(self.src):
            raise Exception("{} is not a folder".format(self.src))

        self.output = open(self.dst, "wb")
        self.build()

        print "Save application to {}".format(self.dst)

    def build(self):
        """Finish parsing process and print statistics
        """
        self.output.write("""<?xml version="1.0" encoding="utf-8"?>\n""")

        self.write_plugin_info()
        self.write_timers()
        self.write_custom_events()
        self.write_databases()
        self.write_resources()
        self.write_macroses()

        self.output.write("</plugin>")

    def open_file(self, path, mode="rb"):
        print "Open {}".format(path)
        return open(path, mode)

    def write_xml(
        self,
        tagname,
        attrs=None,
        data=None,
        close=False,
        indent=0,
        force_cdata=False,
        closing=False
    ):
        self.output.write("{indent}<{closing}{tagname}{attrs}{close}>{data}{closetag}{newline}".format(
            indent=" "*indent,
            tagname=tagname,
            attrs="" if not attrs else (" "+" ".join([u'{}="{}"'.format(k, v) for k, v in attrs.items()])),
            close="/" if close and data is None else "",
            closetag="</{}>".format(tagname) if close and data is not None else "",
            data=cdata(data, force_cdata) if data is not None else "",
            newline="\n" if close or data is None else "",
            closing="/" if closing else ""
        ))

    def write_plugin_info(self):
        info_path = os.path.join(self.src, INFO_JSON)
        icon_path = os.path.join(self.src, PLUGIN_ICON)

        if not os.path.exists(info_path):
            raise Exception("Can't find {}".format(info_path))

        with self.open_file(info_path) as info_file:
            info_json = json.load(info_file)

        if not os.path.exists(icon_path):
            print "Warning! Can't find {}".format(icon_path)

        else:
            with self.open_file(icon_path) as icon_file:
                info_json["picture"] = base64.b64encode(icon_file.read())

        self.write_xml("plugin", attrs=info_json)

    def write_timers(self):
        timers_path = os.path.join(self.src, TIMERS_JSON)

        if not os.path.exists(timers_path):
            print "Warning! Can't find {}".format(timers_path)
            return

        with self.open_file(timers_path) as timers_file:
            timers_json = json.load(timers_file)

        for timer in timers_json:
            self.write_xml("timer", indent=2)
            self.write_xml("name", indent=4, data=timer["name"], close=True)
            self.write_xml("guid", indent=4, data=timer["guid"], close=True)
            self.write_xml("period", indent=4, data=timer["period"], close=True)
            self.write_xml("timer", indent=2, closing=True)

    def write_custom_events(self):
        events_path = os.path.join(self.src, EVENTS_JSON)

        if not os.path.exists(events_path):
            print "Warning! Can't find {}".format(events_path)
            return

        with self.open_file(events_path) as events_file:
            events_json = json.load(events_file)

        for event in events_json:
            self.write_xml("custom_event", indent=2)
            self.write_xml("name", indent=4, data=event["name"], close=True)
            self.write_xml("guid", indent=4, data=event["guid"], close=True)
            self.write_xml("custom_event", indent=2, closing=True)

    def write_databases(self):
        dbs_path = os.path.join(self.src, "Databases")

        if not os.path.exists(dbs_path):
            print "Warning! Can't find {}".format(dbs_path)
            return

        for name in os.listdir(dbs_path):
            self.write_xml("database", indent=2)
            self.write_xml("name", indent=4, data=name, close=True)

            with self.open_file(os.path.join(dbs_path, name)) as db_file:
                self.write_xml("db_source", indent=4, data=base64.b64encode(db_file.read()), close=True)

            self.write_xml("database", indent=2, closing=True)

    def write_resources(self):
        res_path = os.path.join(self.src, "Resources")

        if not os.path.exists(res_path):
            print "Warning! Can't find {}".format(res_path)
            return

        for name in os.listdir(res_path):
            self.write_xml("resource", indent=2)
            self.write_xml("name", indent=4, data=name, close=True)

            with self.open_file(os.path.join(res_path, name)) as res_file:
                self.write_xml("res_source", indent=4, data=base64.b64encode(res_file.read()), close=True)
                
            self.write_xml("resource", indent=2, closing=True)

    def write_macroses(self):
        macroses_path = os.path.join(self.src, "Macroses")

        if not os.path.exists(macroses_path):
            print "Warning! Can't find {}".format(macroses_path)
            return

        for name in os.listdir(macroses_path):
            if ".vscript.vb" not in name:
                continue

            macro = name.split(".vscript.vb")[0]

            meta_path = os.path.join(macroses_path, "{}.json".format(macro))
            icon_path = os.path.join(macroses_path, "{}.icon".format(macro))

            if not os.path.exists(meta_path):
                print "Warning! Can't find {}".format(meta_path)
                continue

            with self.open_file(meta_path) as meta_file:
                meta_json = json.load(meta_file)

            self.write_xml("macro", indent=2)

            for key, value in meta_json.items():
                self.write_xml(key, data=value, indent=4, close=True)

            if os.path.exists(icon_path):
                with self.open_file(icon_path) as icon_file:
                    self.write_xml("macros_picture", data=base64.b64encode(icon_file.read()), indent=4, close=True)

            with self.open_file(os.path.join(macroses_path, name)) as macro_file:
                self.write_xml(
                    "source",
                    data=cgi.escape(macro_file.read(), quote=True),
                    indent=4,
                    close=True)

            self.write_xml("macro", closing=True, indent=2)


def create():
    return Builder().initialize()


if __name__ == "__main__":
    sys.exit(0)
