import ctypes
import subprocess
import threading
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

HPCON = wintypes.HANDLE

PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
INFINITE = 0xFFFFFFFF
ERROR_BROKEN_PIPE = 109


class COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFOW),
        ("lpAttributeList", ctypes.c_void_p),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


kernel32.CreatePipe.argtypes = [
    ctypes.POINTER(wintypes.HANDLE),
    ctypes.POINTER(wintypes.HANDLE),
    ctypes.c_void_p,
    wintypes.DWORD,
]
kernel32.CreatePipe.restype = wintypes.BOOL

kernel32.CreatePseudoConsole.argtypes = [
    COORD,
    wintypes.HANDLE,
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(HPCON),
]
kernel32.CreatePseudoConsole.restype = ctypes.c_long  # HRESULT

kernel32.ClosePseudoConsole.argtypes = [HPCON]
kernel32.ClosePseudoConsole.restype = None

kernel32.InitializeProcThreadAttributeList.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL

kernel32.UpdateProcThreadAttribute.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL

kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
kernel32.DeleteProcThreadAttributeList.restype = None

kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.BOOL,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFOEXW),
    ctypes.POINTER(PROCESS_INFORMATION),
]
kernel32.CreateProcessW.restype = wintypes.BOOL

kernel32.ReadFile.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.c_void_p,
]
kernel32.ReadFile.restype = wintypes.BOOL

kernel32.WriteFile.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.c_void_p,
]
kernel32.WriteFile.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD

kernel32.GetExitCodeProcess.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.GetExitCodeProcess.restype = wintypes.BOOL

kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.TerminateProcess.restype = wintypes.BOOL


def available():
    return hasattr(kernel32, "CreatePseudoConsole")


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


class ConPtyProcess:
    def __init__(self, args, cwd=None, cols=120, rows=40):
        self._h_in_r = wintypes.HANDLE()
        self._h_in_w = wintypes.HANDLE()
        self._h_out_r = wintypes.HANDLE()
        self._h_out_w = wintypes.HANDLE()
        self._hpc = HPCON()
        self._pi = PROCESS_INFORMATION()
        self._exit_code = None
        self._closed = False
        self._lock = threading.Lock()

        self.stdout = _Reader(self)
        self.stdin = _Writer(self)

        self._spawn(args, cwd, cols, rows)

    def _spawn(self, args, cwd, cols, rows):
        if not kernel32.CreatePipe(
            ctypes.byref(self._h_in_r), ctypes.byref(self._h_in_w), None, 0
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel32.CreatePipe(
            ctypes.byref(self._h_out_r), ctypes.byref(self._h_out_w), None, 0
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        size = COORD(cols, rows)
        hr = kernel32.CreatePseudoConsole(
            size, self._h_in_r, self._h_out_w, 0, ctypes.byref(self._hpc)
        )
        if hr != 0:
            raise OSError("CreatePseudoConsole failed (0x%08x)" % (hr & 0xFFFFFFFF))

        kernel32.CloseHandle(self._h_in_r)
        self._h_in_r = wintypes.HANDLE()
        kernel32.CloseHandle(self._h_out_w)
        self._h_out_w = wintypes.HANDLE()

        attr_size = ctypes.c_size_t(0)
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size))
        self._attr_buf = ctypes.create_string_buffer(attr_size.value)
        attr_list = ctypes.cast(self._attr_buf, ctypes.c_void_p)
        if not kernel32.InitializeProcThreadAttributeList(
            attr_list, 1, 0, ctypes.byref(attr_size)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel32.UpdateProcThreadAttribute(
            attr_list,
            0,
            ctypes.c_void_p(PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE),
            self._hpc,
            ctypes.sizeof(HPCON),
            None,
            None,
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        si_ex = STARTUPINFOEXW()
        si_ex.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
        si_ex.lpAttributeList = attr_list

        cmdline = subprocess.list2cmdline(args)
        cmd_buf = ctypes.create_unicode_buffer(cmdline)

        ok = kernel32.CreateProcessW(
            None,
            cmd_buf,
            None,
            None,
            False,
            EXTENDED_STARTUPINFO_PRESENT,
            None,
            cwd,
            ctypes.byref(si_ex),
            ctypes.byref(self._pi),
        )
        kernel32.DeleteProcThreadAttributeList(attr_list)
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

        kernel32.CloseHandle(self._pi.hThread)
        self._pi.hThread = wintypes.HANDLE()

        threading.Thread(target=self._waiter, daemon=True).start()

    def _waiter(self):
        kernel32.WaitForSingleObject(self._pi.hProcess, INFINITE)
        code = wintypes.DWORD(0)
        kernel32.GetExitCodeProcess(self._pi.hProcess, ctypes.byref(code))
        self._exit_code = code.value
        if self._hpc:
            kernel32.ClosePseudoConsole(self._hpc)
            self._hpc = HPCON()

    def _read(self, n):
        buf = ctypes.create_string_buffer(n)
        read = wintypes.DWORD(0)
        ok = kernel32.ReadFile(
            self._h_out_r, buf, n, ctypes.byref(read), None
        )
        if not ok:
            err = ctypes.get_last_error()
            if err in (ERROR_BROKEN_PIPE, 0):
                return b""
            return b""
        if read.value == 0:
            return b""
        return buf.raw[: read.value]

    def _write(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        written = wintypes.DWORD(0)
        kernel32.WriteFile(
            self._h_in_w, data, len(data), ctypes.byref(written), None
        )
        return written.value

    def poll(self):
        return self._exit_code

    def wait(self):
        kernel32.WaitForSingleObject(self._pi.hProcess, INFINITE)
        if self._exit_code is None:
            code = wintypes.DWORD(0)
            kernel32.GetExitCodeProcess(self._pi.hProcess, ctypes.byref(code))
            self._exit_code = code.value
        return self._exit_code

    def terminate(self):
        if self._pi.hProcess:
            kernel32.TerminateProcess(self._pi.hProcess, 1)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
        for h in (self._h_in_w, self._h_out_r, self._pi.hProcess):
            if h:
                kernel32.CloseHandle(h)


def spawn(args, cwd=None, cols=120, rows=40):
    return ConPtyProcess(args, cwd=cwd, cols=cols, rows=rows)
