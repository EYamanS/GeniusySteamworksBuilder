"""POSIX counterpart of conpty.py (macOS / Linux).

Runs a child process attached to a real pseudo-terminal so that steamcmd
flushes its output line by line and shows its interactive prompts (Steam
Guard) instead of block-buffering everything until exit. Exposes the same
minimal interface as conpty.ConPtyProcess / subprocess.Popen that
build_engine.BuildRunner relies on: .stdout.read(n), .stdin.write()/flush(),
.poll(), .wait(), .terminate(), .close().
"""

import fcntl
import os
import pty
import signal
import struct
import subprocess
import termios


def available():
    return os.name == "posix"


class _Reader:
    def __init__(self, proc):
        self._proc = proc

    def read(self, n=1):
        return self._proc._read(n)


class _Writer:
    def __init__(self, proc):
        self._proc = proc

    def write(self, data):
        return self._proc._write(data)

    def flush(self):
        pass


class PosixPtyProcess:
    def __init__(self, args, cwd=None, cols=120, rows=40):
        master, slave = pty.openpty()
        try:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except OSError:
            pass
        try:
            self._proc = subprocess.Popen(
                args,
                cwd=cwd,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
                start_new_session=True,
            )
        except Exception:
            os.close(master)
            os.close(slave)
            raise
        os.close(slave)
        self._master = master
        self._closed = False

        self.stdout = _Reader(self)
        self.stdin = _Writer(self)

    def _read(self, n):
        try:
            return os.read(self._master, n)
        except OSError:
            # EIO once the child exits and the slave end closes: treat as EOF.
            return b""

    def _write(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        try:
            return os.write(self._master, data)
        except OSError:
            return 0

    def poll(self):
        return self._proc.poll()

    def wait(self):
        return self._proc.wait()

    def terminate(self):
        # steamcmd.sh is a wrapper that spawns the real steamcmd binary, so
        # signal the whole process group (start_new_session made us its leader).
        try:
            os.killpg(self._proc.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                self._proc.terminate()
            except OSError:
                pass

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            os.close(self._master)
        except OSError:
            pass


def spawn(args, cwd=None, cols=120, rows=40):
    return PosixPtyProcess(args, cwd=cwd, cols=cols, rows=rows)
