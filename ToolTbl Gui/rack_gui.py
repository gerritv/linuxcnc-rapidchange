#!/usr/bin/env python3
"""RapidChange ATC pocket-map editor.

This program manages only a separate pocket-to-tool mapping file.  It does
not edit PathPilot's tool table.  It is compatible with Python 3.4 / GTK 3,
as supplied with Linux Mint 17.

Usage:
    python3 rack_gui.py [mapping-file] [number-of-pockets]

For example:
    python3 rack_gui.py /home/operator/rack_map.txt 10
"""

from __future__ import print_function

import os
import shutil
import sys
import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


DEFAULT_MAP_FILE = "/home/operator/rack_map.txt"
DEFAULT_POCKETS = 10


class RackGUI(object):
    def __init__(self, glade_file, map_file, number_of_pockets):
        self.map_file = map_file
        self.number_of_pockets = number_of_pockets
        self.pockets = dict((pocket, 0)
                            for pocket in range(1, number_of_pockets + 1))

        self.builder = Gtk.Builder()
        self.builder.add_from_file(glade_file)
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("main_window")
        self.store = self.builder.get_object("pocket_store")
        self.view = self.builder.get_object("pocket_tree")
        self.tool_entry = self.builder.get_object("tool_entry")
        self.pocket_combo = self.builder.get_object("pocket_combo")
        self.status_label = self.builder.get_object("status_label")

        self.load()
        self.refresh_view()
        self.status("Editing {}".format(self.map_file))

    def load(self):
        """Load valid 'pocket,tool' rows. Missing map files are OK."""
        if not os.path.exists(self.map_file):
            return

        try:
            with open(self.map_file, "r") as map_handle:
                for line_number, line in enumerate(map_handle, 1):
                    row = line.strip()
                    if not row or row.startswith(";") or row.startswith("#"):
                        continue
                    fields = row.split(",")
                    if len(fields) != 2:
                        self.status("Ignoring malformed row {}".format(line_number))
                        continue
                    try:
                        pocket = int(fields[0].strip())
                        tool = int(fields[1].strip())
                    except ValueError:
                        self.status("Ignoring non-numeric row {}".format(line_number))
                        continue
                    if pocket not in self.pockets or tool < 0:
                        self.status("Ignoring out-of-range row {}".format(line_number))
                        continue
                    self.pockets[pocket] = tool
        except IOError as error:
            self.status("Could not read map: {}".format(error))

        self.clear_duplicate_tools()

    def clear_duplicate_tools(self):
        """Keep the first occurrence of a tool; empty later duplicates."""
        seen = set()
        for pocket in sorted(self.pockets):
            tool = self.pockets[pocket]
            if tool and tool in seen:
                self.pockets[pocket] = 0
                self.status("T{} was duplicated; pocket {} was emptied".format(
                    tool, pocket))
            elif tool:
                seen.add(tool)

    def save(self):
        """Write all pockets atomically and keep a timestamped backup."""
        directory = os.path.dirname(os.path.abspath(self.map_file))
        if not os.path.isdir(directory):
            self.status("Folder does not exist: {}".format(directory))
            return False

        if os.path.exists(self.map_file):
            backup = "{}.bak.{}".format(self.map_file, time.strftime("%Y%m%d-%H%M%S"))
            try:
                shutil.copy2(self.map_file, backup)
            except IOError as error:
                self.status("Could not make backup: {}".format(error))
                return False

        temporary = self.map_file + ".tmp"
        try:
            with open(temporary, "w") as map_handle:
                map_handle.write("; RapidChange ATC pocket mapping\n")
                map_handle.write("; pocket,tool  (tool 0 means empty)\n")
                for pocket in range(1, self.number_of_pockets + 1):
                    map_handle.write("{},{}\n".format(pocket, self.pockets[pocket]))
                map_handle.flush()
                os.fsync(map_handle.fileno())
            os.rename(temporary, self.map_file)
        except (IOError, OSError) as error:
            try:
                if os.path.exists(temporary):
                    os.remove(temporary)
            except OSError:
                pass
            self.status("Could not save map: {}".format(error))
            return False

        self.status("Saved at {}".format(time.strftime("%H:%M:%S")))
        return True

    def refresh_view(self):
        self.store.clear()
        for pocket in range(1, self.number_of_pockets + 1):
            tool = self.pockets[pocket]
            display_tool = "Empty" if tool == 0 else "T{}".format(tool)
            self.store.append([pocket, tool, display_tool])

        active_pocket = self.pocket_combo.get_active_id()
        self.pocket_combo.remove_all()
        for pocket in range(1, self.number_of_pockets + 1):
            if self.pockets[pocket] == 0:
                self.pocket_combo.append(str(pocket), "Pocket {}".format(pocket))
        if active_pocket is not None and self.pockets.get(int(active_pocket)) == 0:
            self.pocket_combo.set_active_id(active_pocket)
        elif self.pocket_combo.get_model() and len(self.pocket_combo.get_model()):
            self.pocket_combo.set_active(0)

    def entered_tool(self):
        try:
            tool = int(self.tool_entry.get_text().strip())
        except ValueError:
            self.status("Enter a positive, whole tool number")
            return None
        if tool <= 0:
            self.status("Tool number must be greater than zero")
            return None
        return tool

    def selected_free_pocket(self):
        identifier = self.pocket_combo.get_active_id()
        if identifier is None:
            self.status("Choose an empty destination pocket")
            return None
        return int(identifier)

    def find_tool(self, tool):
        for pocket, mapped_tool in self.pockets.items():
            if mapped_tool == tool:
                return pocket
        return None

    def on_assign_btn_clicked(self, widget):
        tool = self.entered_tool()
        if tool is None:
            return
        if self.find_tool(tool) is not None:
            self.status("T{} is already in pocket {}".format(tool, self.find_tool(tool)))
            return
        pocket = self.selected_free_pocket()
        if pocket is None:
            return
        self.pockets[pocket] = tool
        if self.save():
            self.refresh_view()

    def on_remove_btn_clicked(self, widget):
        model, tree_iter = self.view.get_selection().get_selected()
        if tree_iter is None:
            self.status("Select a pocket to empty")
            return
        pocket = model.get_value(tree_iter, 0)
        if self.pockets[pocket] == 0:
            self.status("Pocket {} is already empty".format(pocket))
            return
        tool = self.pockets[pocket]
        self.pockets[pocket] = 0
        if self.save():
            self.refresh_view()
            self.status("Removed T{} from pocket {}".format(tool, pocket))

    def on_remap_btn_clicked(self, widget):
        tool = self.entered_tool()
        if tool is None:
            return
        old_pocket = self.find_tool(tool)
        if old_pocket is None:
            self.status("T{} is not currently in the rack".format(tool))
            return
        new_pocket = self.selected_free_pocket()
        if new_pocket is None:
            return
        self.pockets[old_pocket] = 0
        self.pockets[new_pocket] = tool
        if self.save():
            self.refresh_view()
            self.status("Moved T{} from pocket {} to {}".format(
                tool, old_pocket, new_pocket))

    def on_pocket_tree_cursor_changed(self, widget):
        model, tree_iter = self.view.get_selection().get_selected()
        if tree_iter is not None:
            tool = model.get_value(tree_iter, 1)
            if tool:
                self.tool_entry.set_text(str(tool))

    def on_close_btn_clicked(self, widget):
        Gtk.main_quit()

    def on_main_window_destroy(self, widget):
        Gtk.main_quit()

    def status(self, message):
        self.status_label.set_text(message)
        print(message)

    def run(self):
        self.window.show_all()
        Gtk.main()


def main():
    map_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MAP_FILE
    try:
        number_of_pockets = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_POCKETS
    except ValueError:
        print("The number of pockets must be a whole number.")
        return 2
    if number_of_pockets < 1:
        print("The number of pockets must be at least one.")
        return 2

    script_directory = os.path.dirname(os.path.abspath(__file__))
    glade_file = os.path.join(script_directory, "rack_gui.glade")
    RackGUI(glade_file, map_file, number_of_pockets).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
