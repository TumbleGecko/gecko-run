# Start a DOS program in DOSBox-X and keep its window open when the program fails

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from gecko_run import process


FLATPAK_ID = "com.dosbox_x.DOSBox-X"
NATIVE_COMMAND = "dosbox-x"
# Flatpak cannot share /tmp or /run with an app, so the start files go in the cache folder
CACHE_FOLDER = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "gecko-run"
# DOSBox-X mounts the start files here, away from C and the D a game may want for its CD
START_DRIVE = "Y"
START_BATCH = "RUN.BAT"
# A program still running after this long did not end right after starting
QUICK_EXIT_SECONDS = 5
# This file appears for DOS once the quick exit time has passed
RUNNING_MARKER = "RUNNING"


def find_dosbox_command(folders):
	if shutil.which(NATIVE_COMMAND):
		return [NATIVE_COMMAND]
	if not shutil.which("flatpak"):
		return None
	installed = subprocess.run(["flatpak", "info", FLATPAK_ID], capture_output=True, check=False)
	if installed.returncode != 0:
		return None
	return ["flatpak", "run", *(f"--filesystem={folder}" for folder in folders), FLATPAK_ID]


# The program's own messages stay on screen above the reason, until a key closes the window
def write_start_batch(path, program_name):
	lines = (
		"@echo off",
		"cls",
		"C:",
		program_name,
		"if errorlevel 1 goto failed",
		f"if exist {START_DRIVE}:\\{RUNNING_MARKER} exit",
		"echo.",
		f"echo {program_name} closed right after it started.",
		"goto wait",
		":failed",
		"echo.",
		f"echo {program_name} stopped with an error.",
		":wait",
		"pause",
		"exit",
	)
	path.write_bytes("".join(line + "\r\n" for line in lines).encode("ascii", errors="replace"))


# Returns the DOSBox-X outcome, or None when no DOSBox-X is installed
def run_program(path):
	program_folder = os.path.dirname(path)
	CACHE_FOLDER.mkdir(parents=True, exist_ok=True)
	start_folder = Path(tempfile.mkdtemp(dir=CACHE_FOLDER))
	try:
		command = find_dosbox_command((program_folder, start_folder))
		if command is None:
			return None
		write_start_batch(start_folder / START_BATCH, os.path.basename(path))
		# -nocachedir lets DOS see the running marker that appears while the program runs
		command += [
			"-fastlaunch",
			"-c", f'mount c "{program_folder}"',
			"-c", f'mount {START_DRIVE} "{start_folder}" -nocachedir',
			"-c", f"{START_DRIVE}:\\{START_BATCH}",
		]
		marker = threading.Timer(QUICK_EXIT_SECONDS, (start_folder / RUNNING_MARKER).touch)
		marker.start()
		try:
			return process.run(command, program_folder)
		finally:
			marker.cancel()
	finally:
		shutil.rmtree(start_folder, ignore_errors=True)
