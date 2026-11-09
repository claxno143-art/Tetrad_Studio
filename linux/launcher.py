#!/usr/bin/python3
"""Tetrad Studio: one app process that opens each study tool in its own window.

Usage: launcher.py [suite | list-trainer | opi-tool | opi-example | reader]

All windows share one WebKit context and one data folder
(~/.local/share/russian-study-tools/studio), so the tools see each other's saved
data live. A second launch hands its request to the running instance instead of
starting another process. The first run copies progress over from the old
per-tool folders.
"""
import json
import os
import sys

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2  # noqa: E402

TOOLS = {
    "suite": ("Tetrad Studio", "tetrad-studio", (720, 560)),
    "list-trainer": ("Russian List Trainer", "russian-list-trainer", (1100, 820)),
    "opi-tool": ("OPI Memory Tool", "russian-opi-tool", (1100, 820)),
    "reader": ("Russian Reader", "russian-reader", (1100, 860)),
    "opi-example": ("OPI Memory Tool: Worked Example", "russian-opi-tool", (1100, 820)),
}
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(GLib.get_user_data_dir(), "russian-study-tools")
DATA = os.path.join(BASE, "studio")
CACHE = os.path.join(GLib.get_user_cache_dir(), "russian-study-tools", "studio")
MARKER = os.path.join(DATA, "migrated-v1")


def page_uri(key):
    return GLib.filename_to_uri(os.path.join(HERE, key + ".html"), None)


def make_context(data_dir, cache_dir):
    os.makedirs(data_dir, exist_ok=True)
    manager = WebKit2.WebsiteDataManager(base_data_directory=data_dir, base_cache_directory=cache_dir)
    return WebKit2.WebContext.new_with_website_data_manager(manager)


def make_view(context):
    view = WebKit2.WebView.new_with_context(context)
    s = view.get_settings()
    s.set_enable_html5_local_storage(True)
    s.set_allow_file_access_from_file_urls(True)
    s.set_allow_universal_access_from_file_urls(True)
    s.set_enable_developer_extras(False)
    s.set_enable_back_forward_navigation_gestures(False)
    return view


class Migration:
    """Copies localStorage from the old per-tool data folders into the shared one, once."""

    def __init__(self, context, done):
        self.context, self.done, self.found = context, done, {}
        self.old = [k for k in ("list-trainer", "opi-tool") if os.path.isdir(os.path.join(BASE, k))]
        self.keep = []
        self.next_old()

    def run_js(self, view, js, cb):
        view.evaluate_javascript(js, -1, None, None, None, lambda v, r: cb(v, r))

    def next_old(self):
        if not self.old:
            return self.write_shared()
        key = self.old.pop(0)
        ctx = make_context(os.path.join(BASE, key), os.path.join(GLib.get_user_cache_dir(), "russian-study-tools", key))
        view = make_view(ctx)
        self.keep.append((ctx, view))

        def loaded(v, ev):
            if ev != WebKit2.LoadEvent.FINISHED:
                return
            def got(v2, res):
                try:
                    self.found.update(json.loads(v2.evaluate_javascript_finish(res).to_string()))
                except Exception as e:  # nothing to carry over is fine
                    print("migration read failed:", key, e, file=sys.stderr)
                self.next_old()
            self.run_js(v, "JSON.stringify(Object.assign({}, localStorage))", got)
        view.connect("load-changed", loaded)
        view.load_uri(page_uri("blank"))

    def write_shared(self):
        view = make_view(self.context)
        self.keep.append((None, view))

        def loaded(v, ev):
            if ev != WebKit2.LoadEvent.FINISHED:
                return
            js = ("var d=%s;for(var k in d){if(localStorage.getItem(k)===null)localStorage.setItem(k,d[k]);}'ok'"
                  % json.dumps(self.found))
            def wrote(v2, res):
                try:
                    v2.evaluate_javascript_finish(res)
                    open(MARKER, "w").write("ok\n")
                except Exception as e:
                    print("migration write failed:", e, file=sys.stderr)
                GLib.timeout_add(300, self.finish)  # let WebKit flush storage before windows open
            self.run_js(v, js, wrote)
        view.connect("load-changed", loaded)
        view.load_uri(page_uri("blank"))

    def finish(self):
        self.keep = []
        self.done()
        return False


class ToolWindow(Gtk.ApplicationWindow):
    def __init__(self, studio, key):
        title, icon, size = TOOLS[key]
        super().__init__(application=studio, title=title)
        self.studio, self.key = studio, key
        self.set_icon_name(icon)
        self.set_default_size(*size)
        self.view = make_view(studio.context)
        self.view.connect("decide-policy", self.on_policy)
        self.view.connect("context-menu", lambda *a: True)  # no browser right-click menu
        self.uri = page_uri(key)
        self.view.load_uri(self.uri)
        self.add(self.view)
        self.connect("key-press-event", self.on_key)
        self.full = False

    def on_policy(self, view, decision, kind):
        if kind in (WebKit2.PolicyDecisionType.NAVIGATION_ACTION, WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION):
            uri = decision.get_navigation_action().get_request().get_uri()
            if uri.split("#")[0] == self.uri:
                return False
            if uri.startswith("launch:"):  # buttons in the suite (and links between tools)
                self.studio.open_tool(uri[len("launch:"):])
                if self.key == "suite":
                    GLib.timeout_add(300, lambda: self.close() and False)
            elif not uri.startswith("file://"):
                Gio.AppInfo.launch_default_for_uri(uri, None)
            decision.ignore()  # e.g. a file dropped on the window; the page handles drops itself
            return True
        return False

    def on_key(self, _w, ev):
        ctrl = ev.state & Gdk.ModifierType.CONTROL_MASK
        k = Gdk.keyval_name(ev.keyval)
        if ctrl and k in ("q", "w"):
            self.close()
        elif ctrl and k in ("plus", "equal", "KP_Add"):
            self.view.set_zoom_level(min(3.0, self.view.get_zoom_level() + 0.1))
        elif ctrl and k in ("minus", "KP_Subtract"):
            self.view.set_zoom_level(max(0.5, self.view.get_zoom_level() - 0.1))
        elif ctrl and k in ("0", "KP_0"):
            self.view.set_zoom_level(1.0)
        elif k == "F11":
            self.unfullscreen() if self.full else self.fullscreen()
            self.full = not self.full
        elif k == "F5" or (ctrl and k == "r"):
            self.view.reload()
        else:
            return False
        return True


class Studio(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.github.russianstudy.tetradstudio",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.context = None
        self.ready = False
        self.pending = []

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.context = make_context(DATA, CACHE)
        if os.path.exists(MARKER):
            self.ready = True
        else:
            self.hold()
            self.migration = Migration(self.context, self.migrated)

    def migrated(self):
        self.ready = True
        self.release()
        for k in self.pending:
            self.open_tool(k)
        self.pending = []

    def do_command_line(self, cmd):
        args = cmd.get_arguments()[1:]
        self.open_tool(args[0] if args and args[0] in TOOLS else "suite")
        return 0

    def open_tool(self, key):
        if key not in TOOLS:
            return
        if not self.ready:
            self.pending.append(key)
            return
        for w in self.get_windows():
            if isinstance(w, ToolWindow) and w.key == key:
                w.present()
                return
        w = ToolWindow(self, key)
        w.show_all()
        w.present()


def main():
    GLib.set_prgname("tetrad-studio")  # matches the Tetrad Studio desktop entry so the dock groups every window
    GLib.set_application_name("Tetrad Studio")
    return Studio().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
