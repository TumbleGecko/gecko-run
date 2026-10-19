# The file types gecko-run is registered for, and how shared-mime-info relates types to each other

import os
from pathlib import Path


# Canonical shared-mime-info names, since desktops look defaults up by those
# Linux programs, scripts and AppImages are left to KDE and the AppImage Installer
HANDLED_TYPES = (
	"application/x-msdownload",
	"application/vnd.microsoft.portable-executable",
	"application/x-ms-ne-executable",
	"application/x-msi",
	"application/x-ms-shortcut",
	"application/x-dosexec",
	"application/x-lx-executable",
	"application/x-dos-com",
)


def list_mime_folders():
	data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
	data_folders = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
	return [Path(folder) / "mime" for folder in [data_home, *data_folders.split(":")] if folder]


def read_pairs(name):
	pairs = []
	for folder in list_mime_folders():
		try:
			lines = (folder / name).read_text().splitlines()
		except OSError:
			continue
		pairs.extend(tuple(line.split()) for line in lines if len(line.split()) == 2)
	return pairs


# Breadth first, so a type's own parents come before their parents
# Each text type is also plain text, which shared-mime-info does not write in its files
def list_type_family(content_type):
	aliases = dict(read_pairs("aliases"))
	parents = {}
	for child, parent in read_pairs("subclasses"):
		parents.setdefault(child, []).append(parent)

	family = []
	waiting = [aliases.get(content_type, content_type)]
	while waiting:
		current = waiting.pop(0)
		if current in family:
			continue
		family.append(current)
		waiting.extend(parents.get(current, []))
		if current.startswith("text/"):
			waiting.append("text/plain")
	return family
