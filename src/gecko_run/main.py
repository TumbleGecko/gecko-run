# Read the command line and hand the file or the install over

import argparse
import signal
import sys

from gecko_run import install, routes


# The shell's status for a program ended by SIGTERM
TERMINATED_STATUS = 128 + signal.SIGTERM


# Logging out sends SIGTERM, and exiting normally still removes the DOS start files
def exit_on_terminate(signal_number, frame):
	sys.exit(TERMINATED_STATUS)


def main(arguments):
	signal.signal(signal.SIGTERM, exit_on_terminate)
	parser = argparse.ArgumentParser(prog="gecko-run", description="Start a file the right way for what it really is.")
	parser.add_argument("file", nargs="?", help="the file to start")
	parser.add_argument("--install", action="store_true", help="make gecko-run the double-click app for programs")
	options = parser.parse_args(arguments)
	if options.install:
		return install.install()
	if options.file is None:
		parser.error("a file to start is needed")
	return routes.start(options.file)
