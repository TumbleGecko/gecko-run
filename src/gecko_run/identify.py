# Work out what a file really is from its first bytes, not from its name

import enum
import struct
import subprocess


# How much of the start of a file the checks read
HEADER_SIZE = 4096
ELF_MAGIC = b"\x7fELF"
# AppImage types 1 and 2 put this right after the ELF identification bytes
APPIMAGE_MAGICS = (b"AI\x01", b"AI\x02")
APPIMAGE_MAGIC_OFFSET = 8
SHEBANG = b"#!"
SHORTCUT_MAGIC = b"L\x00\x00\x00\x01\x14\x02\x00"
# Windows Installer files are OLE compound documents, as Word documents are
OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
INSTALLER_DESCRIPTION = "MSI Installer"
DOS_MAGIC = b"MZ"
# A DOS header keeps the offset of a newer Windows header here
NEW_HEADER_POINTER = 0x3C
PE_MAGIC = b"PE\x00\x00"
WIN16_MAGIC = b"NE"
# The optional header right after the 24 byte PE file header tells 32 from 64 bit
PE_FORMAT_OFFSET = 24
PE32_PLUS_FORMAT = 0x20B
# A .com program has no header, so only its name and its not being text tell
DOS_COM_SUFFIX = ".com"


# The kinds of file gecko-run can recognise, named the way a message shows them
class Kind(enum.Enum):
	LINUX_PROGRAM = "Linux program"
	APPIMAGE = "AppImage"
	SCRIPT = "script"
	WINDOWS_64 = "64-bit Windows program"
	WINDOWS_32 = "32-bit Windows program"
	WINDOWS_INSTALLER = "Windows installer"
	WINDOWS_SHORTCUT = "Windows shortcut"
	DOS_PROGRAM = "DOS program"
	OTHER = "file"


def describe(path):
	return run_file_command(["-Lb", path])


def get_content_type(path):
	return run_file_command(["-Lb", "--mime-type", path])


def run_file_command(arguments):
	try:
		finished = subprocess.run(["file", *arguments], capture_output=True, text=True, check=False)
	except OSError:
		return ""
	return finished.stdout.strip()


def identify_dos_header(stream, header):
	if len(header) < NEW_HEADER_POINTER + 4:
		return Kind.DOS_PROGRAM
	(offset,) = struct.unpack_from("<I", header, NEW_HEADER_POINTER)
	stream.seek(offset)
	new_header = stream.read(PE_FORMAT_OFFSET + 2)

	# DOS extender programs have LE or LX headers and remain DOS programs
	if new_header.startswith(WIN16_MAGIC):
		return Kind.WINDOWS_32
	if not new_header.startswith(PE_MAGIC) or len(new_header) < PE_FORMAT_OFFSET + 2:
		return Kind.DOS_PROGRAM
	(pe_format,) = struct.unpack_from("<H", new_header, PE_FORMAT_OFFSET)
	return Kind.WINDOWS_64 if pe_format == PE32_PLUS_FORMAT else Kind.WINDOWS_32


def identify(path):
	with open(path, "rb") as stream:
		header = stream.read(HEADER_SIZE)
		if header.startswith(DOS_MAGIC):
			return identify_dos_header(stream, header)

	if header.startswith(ELF_MAGIC):
		appimage_magic = header[APPIMAGE_MAGIC_OFFSET:APPIMAGE_MAGIC_OFFSET + 3]
		return Kind.APPIMAGE if appimage_magic in APPIMAGE_MAGICS else Kind.LINUX_PROGRAM
	if header.startswith(SHEBANG):
		return Kind.SCRIPT
	if header.startswith(SHORTCUT_MAGIC):
		return Kind.WINDOWS_SHORTCUT
	if header.startswith(OLE_MAGIC) and INSTALLER_DESCRIPTION in describe(path):
		return Kind.WINDOWS_INSTALLER
	if path.lower().endswith(DOS_COM_SUFFIX) and not get_content_type(path).startswith("text/"):
		return Kind.DOS_PROGRAM
	return Kind.OTHER
