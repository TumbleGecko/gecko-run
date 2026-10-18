# Find the Wine for Windows programs, and another one when Proton-GE cannot start a 32-bit program

import os
import re
import shutil
from pathlib import Path


# Proton-GE's new WoW64 build crashes many 32-bit installers at start with this null pointer fault
# Only that exact crash leads to a rerun, so a program failing for its own reasons does not start twice
CRASH_SIGNATURE = "in wow64 32-bit code"
PRIMARY_WINE = Path.home() / ".local/bin/wine"
STEAM_FOLDERS = (
	Path.home() / ".local/share/Steam",
	Path.home() / ".steam/root",
	Path.home() / ".steam/steam",
)
FAVOURED_PROTONS = ("Proton - Experimental", "Proton Hotfix")
PROTON_WINE = "files/bin/wine"
DISTRO_WINE = Path("/usr/bin/wine")


def is_runnable(path):
	return path.is_file() and os.access(path, os.X_OK)


def find_primary_wine():
	if is_runnable(PRIMARY_WINE):
		return PRIMARY_WINE
	found = shutil.which("wine")
	return Path(found) if found else None


# Numbers compare as numbers, so Proton 10.0 sorts after Proton 9.0
def get_version_key(path):
	parts = re.split(r"(\d+)", path.parent.parent.parent.name)
	return [int(part) if part.isdigit() else part for part in parts]


# Steam's Proton Experimental and Hotfix come first, then the newest other Proton and distro Wine last
def list_fallback_wines():
	wines = [
		folder / "steamapps/common" / name / PROTON_WINE for folder in STEAM_FOLDERS for name in FAVOURED_PROTONS
	]
	for folder in STEAM_FOLDERS:
		protons = (folder / "steamapps/common").glob(f"Proton*/{PROTON_WINE}")
		wines.extend(sorted(protons, key=get_version_key, reverse=True))
	wines.append(DISTRO_WINE)
	return wines


def find_fallback_wine(primary):
	for wine in list_fallback_wines():
		if is_runnable(wine) and wine.resolve() != primary.resolve():
			return wine
	return None


# A Proton's folder name reads better than the path to its wine binary
def get_wine_name(wine):
	if wine.parent.name == "bin" and wine.parent.parent.name == "files":
		return wine.parent.parent.parent.name
	return str(wine)
