#!/usr/bin/python
# encoding: utf-8

import base64
import collections
import cStringIO
import json
import os
import shutil
import sys
import xml.parsers.expat

__version__ = "0.0.3"


JSON_INDENT = 4


INFO_JSON = u"__info__.json"
PLUGIN_ICON = u"plugin.icon"
CUSTOM_EVENTS_JSON = u"custom_events.json"
TIMERS_JSON = u"timers.json"
GIT_DIR = u".git"
SVN_DIR = u".svn"


RESERVED_NAMES = (
    INFO_JSON,
    PLUGIN_ICON,
    CUSTOM_EVENTS_JSON,
    TIMERS_JSON,
    GIT_DIR,
    SVN_DIR
)


def encode(data):
    return data.encode("utf-8")


def build_path(*args):
    return os.path.join(*args)


def clear_data(data):
    return data.strip(' \t\n\r')


def clear_dir(path):
    """Remove all folders and files in dir @path
       except .git and .svn
    """
    for node in os.listdir(path):
        if node in (GIT_DIR, SVN_DIR):
            continue

        node_path = os.path.join(path, node)
        (shutil.rmtree if os.path.isdir(node_path) else os.remove)(node_path)


def create_unic_dir_name(app_path):
    """Create directory with unique name
    """
    i = 0
    while os.path.exists(u"{0}{1}".format(app_path, i)):
        i += 1

    return u"{0}{1}".format(app_path, i)


def create_dir(app_path):
    """If folder @name exists then create another new
    """
    if not os.path.exists(app_path):
        os.mkdir(app_path)

    else:
        result = raw_input(u"{} already exists. Do you want to override it? Y or N\n".format(app_path))
        if result.lower() == "y":
            clear_dir(app_path)

        else:
            app_path = create_unic_dir_name(app_path)
            os.mkdir(app_path)
    
    return app_path


class TagHandler(object):

    def __init__(self, tagname, attrs):
        self.tagname = tagname
        self.attrs = attrs

    def child_start(self, tagname, attrs):
        pass

    def child_end(self, tagname):
        pass

    def child_data(self, data):
        pass

    @property
    def parent(self):
        return Parser().tag_handlers[-2]

    def register(self):
        """Add tag handler to stack
        """
        Parser().add_tag_handler_to_stack(self)
        return self

    def unregister(self):
        """Remove tag handler from stack
        """
        Parser().remove_tag_handler_from_stack(self)
        return self

    def __str__(self):
        return self.tagname


class RootHandler(TagHandler):

    def __init__(self):
        pass

    def child_start(self, tagname, attrs):
        if tagname == "plugin":
            attrs["Name"] = "plugin"
            return PluginTagHandler(tagname, attrs).register()

    @property
    def parent(self):
        return None

    def __str__(self):
        return "Root"


class TimerAndEventsTagHandler(TagHandler):

    ATTRS = tuple()

    def __init__(self, *args, **kwargs):
        super(TimerAndEventsTagHandler, self).__init__(*args, **kwargs)
        self.attrs = collections.defaultdict(list)
        self.current_attr = ""
        self.allow_data = False

    def child_start(self, tagname, attrs):
        if tagname in self.ATTRS:
            self.allow_data = True
            self.current_attr = tagname

    def child_end(self, tagname):
        self.allow_data = False

        if tagname in self.ATTRS:
            self.attrs[self.current_attr] = clear_data(u"".join(self.attrs[self.current_attr]))
            self.current_attr = ""

        elif tagname == self.tagname:
            self.save()
            self.unregister()

    def child_data(self, data):
        if self.allow_data:
            self.attrs[self.current_attr].append(encode(data))

    def save(self):
        pass


class TimerTagHandler(TimerAndEventsTagHandler):

    ATTRS = ("name", "period", "guid")

    def save(self):
        self.parent.timers.append(self.attrs)


class CustomEventTagHandler(TimerAndEventsTagHandler):

    ATTRS = ("name", "guid")

    def save(self):
        self.parent.custom_events.append(self.attrs)


class DatabaseAndResourceTagHandler(TagHandler):

    FOLDER = ""
    RES_TAG = ""
    ATTRS = tuple()

    def __init__(self, *args, **kwargs):
        super(DatabaseAndResourceTagHandler, self).__init__(*args, **kwargs)
        self.current_attr = ""
        self.allow_data = False
        self.io = cStringIO.StringIO()
        self.obj_name = []

    def child_start(self, tagname, attrs):
        if tagname in self.ATTRS:
            self.allow_data = True
            self.current_attr = tagname

    def child_end(self, tagname):
        self.allow_data = False
        self.current_attr = ""

        if tagname == "name":
            self.obj_name = clear_data("".join(self.obj_name))

        elif tagname == self.tagname:
            self.save()
            self.unregister()

    def child_data(self, data):
        if self.allow_data:
            if self.current_attr == "name":
                self.obj_name.append(encode(data))

            elif self.current_attr == self.RES_TAG:
                self.io.write(data)

    def save(self):
        Parser().append_to_current_path(self.FOLDER)
        Parser().write_file(
            self.obj_name,
            base64.b64decode(clear_data(self.io.getvalue()))
        )
        Parser().pop_from_current_path()


class DatabaseTagHandler(DatabaseAndResourceTagHandler):

    FOLDER = "Databases"
    RES_TAG = "db_source"
    ATTRS = ("name", "db_source")


class ResourceTagHandler(DatabaseAndResourceTagHandler):

    FOLDER = "Resources"
    RES_TAG = "res_source"
    ATTRS = ("name", "res_source")


class MacrosTagHandler(TagHandler):

    def __init__(self, *args, **kwargs):
        super(MacrosTagHandler, self).__init__(*args, **kwargs)
        self.current_attr = ""
        self.allow_data = False
        self.io = cStringIO.StringIO()
        self.attrs = collections.defaultdict(list)

    def child_start(self, tagname, attrs):
        if tagname in ("name", "class_name", "is_button",
                       "on_board", "guid", "timer_guid",
                       "custom_event_guid", "page", "type",
                       "macros_picture", "source", "description"):

            self.allow_data = True
            self.current_attr = tagname

    def child_end(self, tagname):
        self.allow_data = False

        if tagname in ("name", "class_name", "is_button",
                       "on_board", "guid", "timer_guid",
                       "custom_event_guid", "page", "type", "source"):

            self.attrs[self.current_attr] = clear_data("".join(self.attrs[self.current_attr]))

        elif tagname == "description":
            self.attrs[self.current_attr] = "".join(self.attrs[self.current_attr]).strip(' \t\n\r')

        elif tagname == "macro":
            self.save()
            self.unregister()

        self.current_attr = ""

    def child_data(self, data):
        if self.allow_data:
            if self.current_attr in ("name", "class_name", "is_button",
                                     "on_board", "guid", "timer_guid",
                                     "custom_event_guid", "page", "type",
                                     "source", "description"):

                self.attrs[self.current_attr].append(encode(data))

            elif self.current_attr == "macros_picture":
                self.io.write(data)

    def save(self):
        Parser().append_to_current_path("Macroses")

        Parser().write_file(
            u"{}.vscript.vb".format(self.attrs["name"]),
            self.attrs.pop("source")
        )     

        Parser().write_file(
            u"{}.json".format(self.attrs["name"]),
            json.dumps(
                self.attrs,
                indent=JSON_INDENT
            )
        )

        data = clear_data(self.io.getvalue())
        if data:
            Parser().write_file(
                u"{}.icon".format(self.attrs["name"]),
                base64.b64decode(self.io.getvalue())
            )

        Parser().pop_from_current_path()


class PluginTagHandler(TagHandler):

    def __init__(self, *args, **kwargs):
        super(PluginTagHandler, self).__init__(*args, **kwargs)
        self.timers = []
        self.custom_events = []
        self.create_dirs()

    def create_dirs(self):
        for folder in ("Resources", "Databases", "Macroses"):
            Parser().append_to_current_path(folder)
            Parser().create_folder_from_current_path()
            Parser().pop_from_current_path()

    def child_start(self, tagname, attrs):
        TAG_HANDLERS_MAP = {
            "timer": TimerTagHandler,
            "custom_event": CustomEventTagHandler,
            "database": DatabaseTagHandler,
            "resource": ResourceTagHandler,
            "macro": MacrosTagHandler,
        }

        handler_cls = TAG_HANDLERS_MAP.get(tagname, None)
        if handler_cls:
            handler_cls(tagname, attrs).register()

    def child_end(self, tagname, depth=0):
        if tagname == "plugin":
            self.save()
            self.unregister()

    def save(self):
        Parser().write_file(
            INFO_JSON,
            json.dumps(
                {
                    "author": self.attrs["author"],
                    "description": self.attrs["description"],
                    "guid": self.attrs["guid"],
                    "name": self.attrs["name"],
                    "version": self.attrs["version"]
                },
                indent=JSON_INDENT
            )
        )

        Parser().write_file(
            TIMERS_JSON,
            json.dumps(self.timers, indent=JSON_INDENT)
        )

        Parser().write_file(
            CUSTOM_EVENTS_JSON,
            json.dumps(self.custom_events, indent=JSON_INDENT)
        )

        if self.attrs["picture"]:
            Parser().write_file(
                PLUGIN_ICON,
                base64.b64decode(self.attrs["picture"])
            )


class Parser(object):

    __instance = None

    def __new__(cls, *a, **kwa):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def initialize(self, src="", dst="", debug=False):
        self.debug = debug
        self.src = src
        self.dst = dst

        self.statisitcs = {
            "unknown": 0,
            "files": 0
        }

        self._handlers_stack = []
        self._current_path = []
        self.pages = {}

        return self

    def create_folder_from_current_path(self):
        os.makedirs(self.current_path())

    def current_path(self):
        return build_path(*self._current_path)

    def append_to_current_path(self, path):
        self._current_path.append(path)

    def pop_from_current_path(self):
        return self._current_path.pop()

    def write_file(self, name, data):
        path = build_path(self.current_path(), name)
        print path

        with open(path, "w") as f:
            f.write(data)

    @property
    def current_xml_path(self):
        return u" > ".join(map(str, self.tag_handlers))

    @property
    def current_handler(self):
        return self.tag_handlers[-1]

    @property
    def tag_handlers(self):
        return self._handlers_stack

    def add_tag_handler_to_stack(self, handler):
        if handler not in self.tag_handlers:
            self.tag_handlers.append(handler)

        else:
            raise Exception("Handler register: handler already in stack")

    def remove_tag_handler_from_stack(self, handler):
        if self.tag_handlers[-1] != handler:
            raise Exception("Handler unregister: invalid handler")

        self.tag_handlers.pop()

    def start_element(self, tagname, attrs):
        """New element found
        """
        self.current_handler.child_start(tagname, attrs)

    def end_element(self, tagname):
        """Element closed
        """
        self.current_handler.child_end(tagname)

    def char_data(self, data):
        """Element data
        """
        self.current_handler.child_data(data)

    def start(self):
        """Setup logging and start main process
        """
        self.dst = create_dir(self.dst or u"Plugin")
        self.append_to_current_path(self.dst)

        RootHandler().register()

        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = self.start_element
        p.EndElementHandler = self.end_element
        p.CharacterDataHandler = self.char_data
        p.ParseFile(open(self.src))

        self.done()

    def done(self):
        """Finish parsing process and print statistics
        """
        pass


def create():
    return Parser().initialize()


if __name__ == "__main__":
    sys.exit(0)
