from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path


class SingleInstance:
    def __init__(self, name: str) -> None:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:24]
        self._name = f"galerazo-{digest}"
        self._handle = None
        self._file = None

    def acquire(self) -> bool:
        if self._handle is not None or self._file is not None:
            return True
        if os.name == "nt":
            return self._acquire_windows()
        return self._acquire_posix()

    def release(self) -> None:
        if os.name == "nt":
            self._release_windows()
        else:
            self._release_posix()

    def __enter__(self) -> SingleInstance:
        if not self.acquire():
            raise RuntimeError("Ya hay otra instancia local en ejecucion.")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()

    def _acquire_windows(self) -> bool:
        import ctypes

        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, True, f"Local\\{self._name}")
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 183:
            kernel32.CloseHandle(handle)
            return False
        self._handle = handle
        return True

    def _release_windows(self) -> None:
        if self._handle is None:
            return
        import ctypes

        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.ReleaseMutex(self._handle)
        kernel32.CloseHandle(self._handle)
        self._handle = None

    def _acquire_posix(self) -> bool:
        import fcntl

        lock_path = Path(tempfile.gettempdir()) / f"{self._name}.lock"
        lock_file = lock_path.open("a+", encoding="ascii")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            return False
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        self._file = lock_file
        return True

    def _release_posix(self) -> None:
        if self._file is None:
            return
        import fcntl

        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        self._file.close()
        self._file = None
