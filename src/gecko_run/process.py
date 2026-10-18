# Run a program while passing its error output along and keeping what explains a failure

import collections
import signal
import subprocess
import sys


# Error lines kept to show with a failure
KEPT_LINES = 6
# Signals that mean a stop request, which is no failure
STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)


# How a finished program ended, with its last error lines and the watched texts it printed
class Outcome:
	def __init__(self, status, last_lines, seen_texts):
		self.status = status
		self.last_lines = last_lines
		self.seen_texts = seen_texts

	def has_failed(self):
		if self.status < 0:
			return signal.Signals(-self.status) not in STOP_SIGNALS
		return self.status > 0

	def explain(self):
		if self.status < 0:
			ending = f"It crashed with {signal.Signals(-self.status).name}."
		else:
			ending = f"It ended with status {self.status}."
		if not self.last_lines:
			return ending
		return ending + "\n\nIts last messages were\n" + "\n".join(self.last_lines)


# Reading goes on until each process with the error output open closes it
# Stopping earlier would break the pipe for children that are still writing
def run(command, folder, watched_texts=()):
	process = subprocess.Popen(command, cwd=folder, stderr=subprocess.PIPE)
	last_lines = collections.deque(maxlen=KEPT_LINES)
	seen_texts = set()
	for raw_line in process.stderr:
		sys.stderr.buffer.write(raw_line)
		sys.stderr.buffer.flush()
		line = raw_line.decode(errors="replace").rstrip()
		if line:
			last_lines.append(line)
		seen_texts.update(text for text in watched_texts if text in line)
	process.stderr.close()
	return Outcome(process.wait(), list(last_lines), seen_texts)
