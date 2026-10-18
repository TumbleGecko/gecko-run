# Start each kind of file the way that kind of file runs

import os
import shutil
import subprocess
from pathlib import Path

from gecko_run import content_types, dos, process, wine
from gecko_run.identify import Kind, describe, get_content_type, identify
from gecko_run.messages import notify, show_error


EXIT_SUCCESS = 0
EXIT_FAILURE = 1
APPIMAGE_INSTALLER = Path.home() / ".local/bin/appimage-installer"
DESKTOP_ID = "gecko-run.desktop"
PERMISSION_HINT = "To allow it, right-click it, choose Properties and turn on\nAllow executing file as program."


# Runs a command from the file's own folder and reports a failure, returning gecko-run's exit status
# A failure that printed a watched text is for the calling function to handle
def run_and_report(command, path, watched_texts=()):
	name = os.path.basename(path)
	try:
		outcome = process.run(command, os.path.dirname(path), watched_texts)
	except OSError as error:
		show_error(f"Cannot start {name}", f"{name} could not be started.\n{error.strerror}.")
		return EXIT_FAILURE, None
	if outcome.has_failed() and not outcome.seen_texts:
		show_error(f"{name} stopped", outcome.explain())
	return (EXIT_FAILURE if outcome.has_failed() else EXIT_SUCCESS), outcome


def explain_permission(path, kind):
	name = os.path.basename(path)
	text = f"{name} is a {kind.value}, but it is not marked as executable.\n{PERMISSION_HINT}"
	show_error(f"{name} is not allowed to run", text)
	return EXIT_FAILURE


def start_executable(path, kind):
	if not os.access(path, os.X_OK):
		return explain_permission(path, kind)
	return run_and_report([path], path)[0]


def find_default_app(content_type):
	try:
		command = ["xdg-mime", "query", "default", content_type]
		finished = subprocess.run(command, capture_output=True, text=True, check=False)
	except OSError:
		return ""
	return finished.stdout.strip()


# The file's own type and its parents are tried in turn, skipping the types gecko-run starts
# kioclient opens the file in the app set for the chosen type, so gecko-run does not call itself
def open_elsewhere(path):
	name = os.path.basename(path)
	for content_type in content_types.list_type_family(get_content_type(path)):
		if content_type in content_types.HANDLED_TYPES or find_default_app(content_type) in ("", DESKTOP_ID):
			continue
		if not shutil.which("kioclient"):
			break
		return run_and_report(["kioclient", "exec", path, content_type], path)[0]
	description = describe(path) or "of an unknown type"
	text = f"{name} is not a program gecko-run can start, and no app is set to open it.\nIt is {description}."
	show_error(f"Cannot open {name}", text)
	return EXIT_FAILURE


def start_linux_program(path):
	return start_executable(path, Kind.LINUX_PROGRAM)


def start_script(path):
	if not os.access(path, os.X_OK):
		return open_elsewhere(path)
	return run_and_report([path], path)[0]


def start_appimage(path):
	installer = APPIMAGE_INSTALLER if os.access(APPIMAGE_INSTALLER, os.X_OK) else shutil.which("appimage-installer")
	if not installer:
		return start_executable(path, Kind.APPIMAGE)
	return run_and_report([str(installer), path], path)[0]


def find_wine_or_explain(path):
	primary = wine.find_primary_wine()
	if primary is None:
		name = os.path.basename(path)
		show_error(f"Cannot start {name}", f"{name} is a Windows file, and Wine is not installed.")
	return primary


# wine start /unix opens the file through the Windows shell, as installers and shortcuts expect
def start_windows_file(path):
	primary = find_wine_or_explain(path)
	if primary is None:
		return EXIT_FAILURE
	return run_and_report([str(primary), "start", "/unix", path], path)[0]


# Run from its own folder, where installers look for their data, and rerun under another Wine on the WoW64 crash
def start_windows_32(path):
	primary = find_wine_or_explain(path)
	if primary is None:
		return EXIT_FAILURE
	name = os.path.basename(path)
	status, outcome = run_and_report([str(primary), name], path, (wine.CRASH_SIGNATURE,))
	if outcome is None or not outcome.seen_texts:
		return status

	crashed = "Proton-GE crashed on this 32-bit program, a known bug of its new WoW64 mode."
	fallback = wine.find_fallback_wine(primary)
	if fallback is None:
		show_error(f"Cannot run {name}", f"{crashed}\nNo other Wine was found, install a Steam Proton and try again.")
		return EXIT_FAILURE
	notify(f"Retrying {name} under another Wine", f"{crashed}\nRunning it under {wine.get_wine_name(fallback)}.")
	return run_and_report([str(fallback), name], path)[0]


def start_dos_program(path):
	name = os.path.basename(path)
	try:
		outcome = dos.run_program(path)
	except OSError as error:
		show_error(f"Cannot start {name}", f"DOSBox-X could not be started.\n{error.strerror}.")
		return EXIT_FAILURE
	if outcome is None:
		show_error(f"Cannot start {name}", f"{name} is a DOS program, and DOSBox-X is not installed.\n"
			f"Install it with\nflatpak install flathub {dos.FLATPAK_ID}")
		return EXIT_FAILURE
	if outcome.has_failed():
		show_error("DOSBox-X stopped", outcome.explain())
		return EXIT_FAILURE
	return EXIT_SUCCESS


STARTERS = {
	Kind.LINUX_PROGRAM: start_linux_program,
	Kind.SCRIPT: start_script,
	Kind.APPIMAGE: start_appimage,
	Kind.WINDOWS_64: start_windows_file,
	Kind.WINDOWS_INSTALLER: start_windows_file,
	Kind.WINDOWS_SHORTCUT: start_windows_file,
	Kind.WINDOWS_32: start_windows_32,
	Kind.DOS_PROGRAM: start_dos_program,
	Kind.OTHER: open_elsewhere,
}


def start(file):
	path = os.path.realpath(file)
	name = os.path.basename(path)
	if not os.path.isfile(path):
		show_error(f"Cannot open {name}", f"{path} is not a file that exists.")
		return EXIT_FAILURE
	try:
		kind = identify(path)
	except OSError as error:
		show_error(f"Cannot open {name}", f"{name} could not be read.\n{error.strerror}.")
		return EXIT_FAILURE
	return STARTERS[kind](path)
