import argparse
import subprocess
import os
import pty
import select
import shutil
import socket
import sys
import termios
import time
import threading
import tempfile
import tty

HELPERDIR = os.path.dirname(os.path.abspath(__file__))
if HELPERDIR not in sys.path:
    sys.path.insert(0, HELPERDIR)
APPBASE_DIR = "/testrunnerapp"
if APPBASE_DIR not in sys.path:
    sys.path.insert(0, APPBASE_DIR)
try:
    import appstate as processreg
except ImportError:
    class processreg:
        register = staticmethod(lambda *a, **k: None)
        unregister = staticmethod(lambda *a, **k: None)

TESTSRC_BASEDIR = "/testsrc"

# Prefer a vendored dgnova (disk_artifacts/bin/dgnova) if present, falling back to PATH. 
_VENDORED_DGNOVA = os.path.join(TESTSRC_BASEDIR, "disk_artifacts", "bin", "dgnova")
DGNOVA_BIN = _VENDORED_DGNOVA if os.path.exists(_VENDORED_DGNOVA) else "dgnova"

DEFAULT_DISK_IMAGE = os.path.join(TESTSRC_BASEDIR, "sourcedir/nova_rdos/rdos_d31.dsk")

# dgnova console emulation (the RDOS boot banner, "Filename?"/Date/Time
# prompts, and the "R" prompt) only behaves correctly when its stdio is a
# real tty 
DEFAULT_BOOT_SCRIPT = """\
{memory_line}attach dkp0 {disk_image}
set tti dasher
boot dkp0
"""


class NovaSimhInstance:
    def __init__(self, name, disk_image=None, script_path=None, memory=None,
                 binary=None, cwd=None, live_path=None):
        self.name = name
        self.disk_image = disk_image or DEFAULT_DISK_IMAGE
        self.script_path = script_path
        # dgnova defaults to 32KW; pass e.g. "60k" (its max) for programs
        # like the RDOS COBOL compiler that need more than the default.
        self.memory = memory
        # A project can supply its own simulator build - sourcedir/nova_fb 
        self.binary = binary or DGNOVA_BIN
        # SIMH resolves relative paths in a script (e.g. "set fb prefix=
        # output/cursor") against its own cwd, so a project driving its own
        # script needs to run from the project directory.
        self.cwd = cwd
        # nova_fb's live view sink
        self.live_path = live_path
        self.process = None
        self.pid = None
        self.master_fd = None
        self.buf = ""
        self.reader_thread = None
        self._stop_reader = False
        self._generated_script = None
        self.console_sock_path = None
        self._sock = None
        self._accept_thread = None
        self._clients = []
        self._clients_lock = threading.Lock()

    def _build_script(self):
        if self.script_path:
            if not self.live_path:
                return self.script_path
            # "set fb live=" has to run before the program does
            return self._wrapper_script(
                f"set fb live={self.live_path}\ndo {self.script_path}\n")
        memory_line = f"set cpu {self.memory}\n" if self.memory else ""
        script_text = DEFAULT_BOOT_SCRIPT.format(memory_line=memory_line, disk_image=self.disk_image)
        if self.live_path:
            script_text = f"set fb live={self.live_path}\n" + script_text
        return self._wrapper_script(script_text)

    def _wrapper_script(self, script_text):
        fd, path = tempfile.mkstemp(prefix=f"simh_{self.name}_", suffix=".ini")
        with os.fdopen(fd, "w") as f:
            f.write(script_text)
        self._generated_script = path
        return path

    def start(self):
        script = self._build_script()
        args = [self.binary, script]
        try:
            master_fd, slave_fd = pty.openpty()
            self.process = subprocess.Popen(
                args,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                cwd=self.cwd,
            )
            os.close(slave_fd)
            self.master_fd = master_fd
            self.pid = self.process.pid
            processreg.register(self.name, self.process, source="simh")
            print("SIMH (dgnova) PID IS: ", self.pid, flush=True)
            print("start command is", args, flush=True)

            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            return True
        except Exception as e:
            self.buf += str(e)
            return False

    def _read_loop(self):
        while not self._stop_reader:
            try:
                r, _, _ = select.select([self.master_fd], [], [], 0.5)
            except (OSError, ValueError):
                break
            if self.master_fd in r:
                try:
                    data = os.read(self.master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                self.buf += data.decode(errors="replace")
                self._tee(data)


    def _tee(self, data):
        """Fan console output out to any attached terminal windows.
        """
        with self._clients_lock:
            clients = list(self._clients)
        for conn in clients:
            try:
                conn.sendall(data)
            except Exception:
                self._drop_client(conn)

    def _drop_client(self, conn):
        with self._clients_lock:
            if conn in self._clients:
                self._clients.remove(conn)
        try:
            conn.close()
        except Exception:
            pass

    def open_console_relay(self, sock_path):
        """Serve this instance's console on a Unix socket. Returns the path.
        """
        if self.console_sock_path:
            return self.console_sock_path
        if os.path.exists(sock_path):
            os.unlink(sock_path)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(sock_path)
        srv.listen(4)
        srv.settimeout(0.5)
        self._sock = srv
        self.console_sock_path = sock_path
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        return sock_path

    def _accept_loop(self):
        while not self._stop_reader and self._sock is not None:
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with self._clients_lock:
                self._clients.append(conn)
            # A terminal that attaches late is otherwise looking at a blank
            # window . Replay the recent console so it opens on the prompt.
            try:
                conn.sendall(self.buf[-4000:].encode(errors="replace"))
            except Exception:
                self._drop_client(conn)
                continue
            threading.Thread(target=self._client_loop, args=(conn,),
                             daemon=True).start()

    def _client_loop(self, conn):
        while not self._stop_reader:
            try:
                data = conn.recv(1024)
            except OSError:
                break
            if not data:
                break
            if self.master_fd is None:
                break
            try:
                os.write(self.master_fd, data)
            except OSError:
                break
        self._drop_client(conn)

    def close_console_relay(self):
        with self._clients_lock:
            clients, self._clients = list(self._clients), []
        for conn in clients:
            try:
                conn.close()
            except Exception:
                pass
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        if self.console_sock_path and os.path.exists(self.console_sock_path):
            try:
                os.unlink(self.console_sock_path)
            except OSError:
                pass
        self.console_sock_path = None

    def wait_for(self, phrase, timeout=15):
        start = time.time()
        while time.time() - start < timeout:
            if phrase in self.buf:
                return True
            if self.process.poll() is not None:
                return phrase in self.buf
            time.sleep(0.2)
        return False

    def send_command(self, cmd_text):
        if self.master_fd is not None:
            os.write(self.master_fd, (cmd_text + "\r").encode())

    def break_to_scp(self):
        # Ctrl-E is SIMH's default WRU character; it interrupts the running
        # simulation and drops back to the SCP ("sim>") command prompt.
        if self.master_fd is not None:
            os.write(self.master_fd, b"\x05")
            time.sleep(0.5)

    def boot_to_rdos(self, date=None, time_str=None, timeout=30):
        """Drives the fixed prompt sequence dgnova/RDOS presents on cold boot:
        Filename? -> [optional "Partition in use" nag] -> Date -> Time -> R
        """
        date = date or time.strftime("%m/%d/%Y")
        time_str = time_str or time.strftime("%H:%M:%S")

        if not self.wait_for("Filename?", timeout):
            return False
        self.send_command("")

        if self.wait_for("Type C to continue", 5):
            self.send_command("C")

        if not self.wait_for("Date", timeout):
            return False
        self.send_command(date)

        if not self.wait_for("Time", timeout):
            return False
        self.send_command(time_str)

        return self.wait_for("\nR", timeout)

    def stop(self):
        self._stop_reader = True
        processreg.unregister(self.name)
        self.close_console_relay()
        if self.process and self.process.poll() is None:
            try:
                self.break_to_scp()
                self.send_command("quit")
                self.process.wait(timeout=5)
            except Exception:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except Exception:
                    self.process.kill()
                    self.process.wait()
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
        if self._generated_script and os.path.exists(self._generated_script):
            os.remove(self._generated_script)


# NovaSimhInstance owns the pty master for the
# life of the run and its reader thread is what every test_novascreensearch
# assertion reads from. A second process cannot open that master

QUIT = b"\x1d"                                   # Ctrl-]


def connect(path, wait):
    """Wait for the relay socket, since the terminal may open before it."""
    deadline = time.time() + wait
    last = None
    while time.time() < deadline:
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(path)
            return s
        except OSError as exc:
            last = exc
            time.sleep(0.25)
    raise SystemExit("novaterm: could not connect to %s (%s)" % (path, last))


def novaterm_main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--socket", required=True, help="console relay socket")
    ap.add_argument("--wait", type=float, default=30.0,
                    help="seconds to wait for the socket to appear")
    ap.add_argument("--banner", default="",
                    help="line printed above the console, for the human")
    args = ap.parse_args(argv)

    sock = connect(args.socket, args.wait)
    if args.banner:
        sys.stdout.write(args.banner.rstrip("\n") + "\r\n")
        sys.stdout.flush()

    stdin = sys.stdin.fileno()
    saved = None
    try:
        saved = termios.tcgetattr(stdin)
        tty.setraw(stdin)
    except Exception:
        # Not a tty (piped, or run outside a terminal): still usable one-way.
        saved = None

    try:
        while True:
            r, _, _ = select.select([stdin, sock], [], [], 0.5)
            if sock in r:
                data = sock.recv(4096)
                if not data:
                    break
                os.write(sys.stdout.fileno(), data)
            if stdin in r:
                data = os.read(stdin, 1024)
                if not data or QUIT in data:
                    break
                sock.sendall(data)
    except OSError:
        pass
    finally:
        if saved is not None:
            termios.tcsetattr(stdin, termios.TCSADRAIN, saved)
        try:
            sock.close()
        except Exception:
            pass

    # The window closing the instant the run ends hides whatever the console
    # said last, which is usually the interesting part.
    sys.stdout.write("\r\n[novaterm] console closed -- press RETURN\r\n")
    sys.stdout.flush()
    try:
        sys.stdin.readline()
    except Exception:
        pass
    return 0

# NovaTermProcess opens an xterm on the user's desktop attached to a Nova's
# SIMH console.

NOVATERM_PY = os.path.abspath(__file__)

# xterm first: it is the only one of these that reliably STAYS the process it
# started, so process.poll() means what it says. xfce4-terminal hands off to an
# already-running server and exits immediately, which would look like a crash.
TERMINALS = ["xterm", "x-terminal-emulator"]


class NovaTermProcess(object):
    def __init__(self, name="nova_terminal", sock_path=None, title=None,
                 geometry="100x30", font_size=14, wait=30.0, python=None,
                 keep_open=False, banner=""):
        self.name = name
        self.sock_path = sock_path
        self.title = title or "Nova console -- %s" % name
        self.geometry = geometry
        self.font_size = font_size
        self.wait = wait
        self.keep_open = keep_open
        self.banner = banner
        self.python = python or sys.executable or "python3"
        self.display = None
        self.terminal = None
        self.process = None
        self.pid = None

    def _resolve_display(self):
        try:
            from displayhelpers import resolve_display
            return resolve_display(os.environ.get("DISPLAY"))
        except Exception:
            return os.environ.get("DISPLAY") or "(unset)"

    def _argv(self):
        inner = [self.python, NOVATERM_PY,
                 "--socket", self.sock_path,
                 "--wait", str(self.wait)]
        if self.banner:
            inner += ["--banner", self.banner]
        argv = [self.terminal, "-T", self.title, "-geometry", self.geometry]
        if os.path.basename(self.terminal) == "xterm":
            # A framebuffer demo is something people lean in to read; the
            # default 6x13 bitmap font on a HiDPI RDP session is not that.
            argv += ["-fa", "monospace", "-fs", str(self.font_size),
                     "-bg", "black", "-fg", "white"]
        return argv + ["-e"] + inner

    def start(self):
        """Launch the terminal. Returns (ok, message)."""
        if not self.sock_path:
            return False, "NovaTermProcess needs a console relay socket path"
        if not os.path.exists(NOVATERM_PY):
            return False, "novaterm.py missing at %s" % NOVATERM_PY
        self.terminal = next((t for t in TERMINALS if shutil.which(t)), None)
        if self.terminal is None:
            return False, ("no terminal emulator found (looked for %s)"
                           % ", ".join(TERMINALS))
        self.display = self._resolve_display()
        env = dict(os.environ)
        env["DISPLAY"] = self.display
        try:
            self.process = subprocess.Popen(
                self._argv(), env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                close_fds=True)
        except Exception as exc:
            return False, "Could not launch %s: %s" % (self.terminal, exc)
        self.pid = self.process.pid
        processreg.register(self.name, self.process, source="nova_terminal")

        # It exits at once on an unreachable X display; a moment's grace turns
        # that into a message rather than a window that never appeared.
        time.sleep(1.0)
        if self.process.poll() is not None:
            err = ""
            try:
                err = (self.process.stderr.read() or b"").decode(errors="replace")
            except Exception:
                pass
            return False, ("%s exited immediately on DISPLAY %s\n%s"
                           % (self.terminal, self.display, err.strip()[-600:]))

        return True, ("%s (pid %s) attached to %s on DISPLAY %s%s"
                      % (self.name, self.pid, self.sock_path, self.display,
                         " (kept open after the run)" if self.keep_open else ""))

    def is_alive(self):
        return self.process is not None and self.process.poll() is None

    def stop(self):
        if self.process is None:
            return
        processreg.unregister(self.name)
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None






# this stuff should be moved into its own file eventually

def _default_cully_llvm_dir():
    return os.path.join(TESTSRC_BASEDIR, "sourcedir", "cully_llvm")


def nova_llvm_toolchain_paths(cully_llvm_dir=None):
    """Resolve nova-cc/_toolchain paths under a cully_llvm checkout
    (defaults to sourcedir/cully_llvm). 
    
    safe to call even when cully_llvm/ or its
    _toolchain/ don't exist."""
    base = cully_llvm_dir or _default_cully_llvm_dir()
    toolchain_dir = os.path.join(base, "_toolchain")
    return {
        "nova_cc": os.path.join(toolchain_dir, "nova-llvm-backend",
                                 "nova-toolchain", "nova-cc"),
        "llvm_build": os.path.join(toolchain_dir, "llvm-build"),
        "dgasm_dir": os.path.join(toolchain_dir, "dgasm", "build"),
    }


def compile_via_nova_llvm(src_path, out_path, cpu="nova3", cully_llvm_dir=None,
                           header_lines=None, footer_lines=None, timeout=120):
    """Compile one C source through cullyrichard's nova-llvm-backend
    (nova-cc -t <cpu>) into a SIMH deposit script 
    

    Returns (bool, str)
    
    a missing/unbuilt is reported, not raised as error. 
    a caller gets a step error message returned if toolchain not present
    """
    if not src_path:
        return False, "compile_via_nova_llvm: no src_path given"
    if not os.path.exists(src_path):
        return False, "compile_via_nova_llvm: src not found: %s" % src_path
    if not out_path:
        return False, "compile_via_nova_llvm: no out_path given"

    paths = nova_llvm_toolchain_paths(cully_llvm_dir)
    nova_cc = paths["nova_cc"]
    if not os.path.exists(nova_cc):
        return False, (
            "compile_via_nova_llvm: no nova-cc at %s -- build "
            "cully_llvm/_toolchain/ first (see cully_llvm/NOTES.txt), or "
            "has sourcedir/cully_llvm been removed/not deployed here?"
            % nova_cc
        )

    env = dict(os.environ)
    env["LLVM_BUILD"] = paths["llvm_build"]
    env["PATH"] = paths["dgasm_dir"] + ":" + env.get("PATH", "")

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    fd, work_simh = tempfile.mkstemp(prefix="nova_llvm_", suffix=".simh")
    os.close(fd)
    try:
        try:
            r = subprocess.run(
                [nova_cc, "-t", cpu, "-o", work_simh, src_path],
                capture_output=True, text=True, env=env, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, "compile_via_nova_llvm: nova-cc timed out after %ss" % timeout
        if r.returncode != 0 or not os.path.exists(work_simh):
            detail = (r.stdout + r.stderr).strip()
            return False, "nova-cc failed (exit %s): %s" % (r.returncode, detail)
        with open(work_simh) as f:
            body = f.read()
    finally:
        try:
            os.remove(work_simh)
        except OSError:
            pass

    with open(out_path, "w") as f:
        for line in (header_lines or []):
            f.write(line.rstrip("\n") + "\n")
        f.write(body)
        if not body.endswith("\n"):
            f.write("\n")
        for line in (footer_lines or []):
            f.write(line.rstrip("\n") + "\n")

    return True, "wrote %s" % out_path


if __name__ == "__main__":
    sys.exit(novaterm_main())
