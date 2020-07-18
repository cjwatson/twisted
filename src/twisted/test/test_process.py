from unittest import skipIf

    fcntl = None  # type: ignore[assignment]

try:
    from twisted.internet.process import (
        ProcessReader, ProcessWriter, PTYProcess)
except ImportError:
    process = None  # type: ignore[misc,assignment]
    ProcessReader = object  # type: ignore[misc,assignment]
    ProcessWriter = object  # type: ignore[misc,assignment]
    PTYProcess = object  # type: ignore[misc,assignment]
from twisted.python.compat import networkString, bytesEnviron
pyExe = FilePath(sys.executable).path
properEnv = dict(os.environ)
properEnv["PYTHONPATH"] = os.pathsep.join(sys.path)
    programName = b""  # type: bytes
            self, pyExe, [pyExe, "-u", "-m", self.programName] + argv,
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")
@skipIf(runtime.platform.getType() != 'win32',
        "Only runs on Windows")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")
@skipIf(runtime.platform.getType() != 'posix',
        "Only runs on POSIX platform")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")

@skipIf(runtime.platform.getType() != 'posix',
        "Only runs on POSIX platform")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")
    @skipIf(runtime.platform.isMacOSX(),
            "Test is flaky from a Darwin bug. See #8840.")

class DumbProcessWriter(ProcessWriter):
    """
    A fake L{ProcessWriter} used for tests.
    """

    def startReading(self):
        Here's the faking: don't do anything here.

class DumbProcessReader(ProcessReader):
    """
    A fake L{ProcessReader} used for tests.
    """

    def startReading(self):
        Here's the faking: don't do anything here.

class DumbPTYProcess(PTYProcess):
    """
    A fake L{PTYProcess} used for tests.
    """

    def startReading(self):
        Here's the faking: don't do anything here.
@skipIf(runtime.platform.getType() != 'posix',
        "Only runs on POSIX platform")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")
@skipIf(runtime.platform.getType() != 'posix',
        "Only runs on POSIX platform")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")
@skipIf(runtime.platform.getType() != 'win32',
        "Only runs on Windows")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")
        pyExe = FilePath(sys.executable).path
@skipIf(runtime.platform.getType() != 'win32',
        "Only runs on Windows")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")

@skipIf(runtime.platform.getType() != 'win32',
        "Only runs on Windows")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")

        pyExe = FilePath(sys.executable).path
@skipIf(runtime.platform.getType() != 'win32',
        "Only runs on Windows")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")
@skipIf(not interfaces.IReactorProcess(reactor, None),
        "reactor doesn't support IReactorProcess")

            if runtime.platform.isWindows():
                self.assertIn(b"OSError", errput)
                self.assertIn(b"22", errput)
                self.assertIn(b'BrokenPipeError', errput)