# Copy gecko-run into the home folder and make it the double-click app for the types it handles

import os
import shutil
import subprocess
from pathlib import Path

from gecko_run import content_types
from gecko_run.routes import DESKTOP_ID, EXIT_FAILURE, EXIT_SUCCESS


SOURCE_FOLDER = Path(__file__).resolve().parent.parent.parent
# The same data folder xdg-mime and KDE read, so each part ends up where the others look
DATA_FOLDER = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
INSTALL_FOLDER = DATA_FOLDER / "gecko-run"
COMMAND_LINK = Path.home() / ".local/bin/gecko-run"
APPLICATIONS_FOLDER = DATA_FOLDER / "applications"
MIME_FOLDER = DATA_FOLDER / "mime"
MIME_PACKAGE = MIME_FOLDER / "packages/gecko-run.xml"

# shared-mime-info gives .com files no type, so this package names them
COM_TYPE_PACKAGE = """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
	<mime-type type="application/x-dos-com">
		<comment>DOS program</comment>
		<glob pattern="*.com"/>
	</mime-type>
</mime-info>
"""


def write_desktop_entry():
	types = "".join(f"{content_type};" for content_type in content_types.HANDLED_TYPES)
	entry = (
		"[Desktop Entry]\n"
		"Type=Application\n"
		"Name=gecko-run\n"
		"Comment=Start a program the right way for what it really is\n"
		f"Exec={COMMAND_LINK} %f\n"
		"Icon=system-run\n"
		"Terminal=false\n"
		"NoDisplay=true\n"
		f"MimeType={types}\n"
	)
	APPLICATIONS_FOLDER.mkdir(parents=True, exist_ok=True)
	(APPLICATIONS_FOLDER / DESKTOP_ID).write_text(entry)


# Running the installed copy again keeps the files in place
def copy_program():
	if SOURCE_FOLDER == INSTALL_FOLDER.resolve():
		return
	shutil.rmtree(INSTALL_FOLDER, ignore_errors=True)
	shutil.copytree(SOURCE_FOLDER / "src", INSTALL_FOLDER / "src", ignore=shutil.ignore_patterns("__pycache__"))
	shutil.copy2(SOURCE_FOLDER / "gecko-run", INSTALL_FOLDER / "gecko-run")
	COMMAND_LINK.parent.mkdir(parents=True, exist_ok=True)
	COMMAND_LINK.unlink(missing_ok=True)
	COMMAND_LINK.symlink_to(INSTALL_FOLDER / "gecko-run")


# kbuildsycoca6 refreshes the cache KDE reads default apps from
def list_registration_commands():
	return (
		["update-mime-database", str(MIME_FOLDER)],
		["update-desktop-database", str(APPLICATIONS_FOLDER)],
		["xdg-mime", "default", DESKTOP_ID, *content_types.HANDLED_TYPES],
		["kbuildsycoca6"],
	)


def install():
	copy_program()
	MIME_PACKAGE.parent.mkdir(parents=True, exist_ok=True)
	MIME_PACKAGE.write_text(COM_TYPE_PACKAGE)
	write_desktop_entry()

	failed = False
	for command in list_registration_commands():
		try:
			finished = subprocess.run(command, stdout=subprocess.DEVNULL, check=False)
		except OSError as error:
			print(f"gecko-run: {command[0]} is missing, {error.strerror}")
			failed = True
			continue
		if finished.returncode != 0:
			print(f"gecko-run: {' '.join(command)} failed with status {finished.returncode}")
			failed = True
	if failed:
		return EXIT_FAILURE
	print(f"gecko-run is installed as {COMMAND_LINK} and opens {len(content_types.HANDLED_TYPES)} file types")
	return EXIT_SUCCESS
