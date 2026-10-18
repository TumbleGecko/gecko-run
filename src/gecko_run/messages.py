# Tell the user what happened, since a double-clicked file has no console

import shutil
import subprocess
import sys


APP_NAME = "gecko-run"
NOTIFICATION_ICON = "system-run"
POPUP_SECONDS = "8"


def log(text):
	print(f"{APP_NAME}: {text}", file=sys.stderr, flush=True)


def run_quietly(command):
	subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def notify(title, text):
	log(f"{title}. {text}")
	if shutil.which("notify-send"):
		run_quietly(["notify-send", "-a", APP_NAME, "-i", NOTIFICATION_ICON, title, text])
	elif shutil.which("kdialog"):
		run_quietly(["kdialog", "--title", title, "--passivepopup", text, POPUP_SECONDS])


# Errors wait in a dialog until read, and only fall back to a notification without kdialog
def show_error(title, text):
	log(f"{title}. {text}")
	if shutil.which("kdialog"):
		run_quietly(["kdialog", "--title", title, "--error", text])
	elif shutil.which("notify-send"):
		run_quietly(["notify-send", "-a", APP_NAME, "-u", "critical", "-i", "dialog-error", title, text])
