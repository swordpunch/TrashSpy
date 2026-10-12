"""
TrashSpy for Windows.
- History: deletion logger for watched folders (polling monitor -> SQLite).
- Recently deleted: NTFS USN journal scan (needs admin, shows deletions
  of the last days/weeks without prior monitoring).
Run: python deleted_viewer.py
"""
import ctypes
import os
import sqlite3
import sys
import threading
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from lang import S, CODES, NAMES, app_dir, get_lang, save_lang

APP_DIR = app_dir()
DB_PATH = APP_DIR / "deletion_log.db"
EPOCH_DIFF = 116444736000000000  # 1601-01-01 -> 1970-01-01 in 100ns units


def filetime_to_local(ft: int) -> datetime:
    us = (ft - EPOCH_DIFF) // 10
    return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc).astimezone().replace(tzinfo=None)


# ---------- NTFS USN journal (recently deleted, no monitoring needed) ----------
def _ctl_code(dev, func, method, access):
    return (dev << 16) | (access << 14) | (func << 2) | method


FSCTL_QUERY_USN_JOURNAL = 0x900F4  # == _ctl_code(9, 61, 0, 0)
FSCTL_ENUM_USN_DATA = _ctl_code(9, 44, 3, 0)  # 0x900B3
FSCTL_READ_USN_JOURNAL = _ctl_code(9, 46, 3, 0)  # 0x900BB
USN_REASON_FILE_DELETE = 0x200
ATTR_DIRECTORY = 0x10
ERROR_HANDLE_EOF = 38
FRN_INDEX_MASK = 0xFFFFFFFFFFFF  # low 48 bits of FRN = MFT index (root = 5)


def _frn_index(frn64: int) -> int:
    return frn64 & FRN_INDEX_MASK

_k32 = ctypes.windll.kernel32
_k32.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                                 wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                 ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
_k32.DeviceIoControl.restype = wintypes.BOOL


class _MFTEnumData(ctypes.Structure):
    _fields_ = [("StartFileReferenceNumber", ctypes.c_uint64),
                ("LowUsn", ctypes.c_int64),
                ("HighUsn", ctypes.c_int64),
                ("MinMajorVersion", ctypes.c_uint16),
                ("MaxMajorVersion", ctypes.c_uint16)]


class _ReadUsnData(ctypes.Structure):
    _fields_ = [("StartUsn", ctypes.c_int64),
                ("ReasonMask", ctypes.c_uint32),
                ("ReturnOnlyOnClose", ctypes.c_uint32),
                ("Timeout", ctypes.c_uint64),
                ("BytesToWaitFor", ctypes.c_uint64),
                ("UsnJournalID", ctypes.c_uint64)]


class _UsnJournalData(ctypes.Structure):
    _fields_ = [("UsnJournalID", ctypes.c_uint64),
                ("FirstUsn", ctypes.c_int64),
                ("NextUsn", ctypes.c_int64),
                ("LowestValidUsn", ctypes.c_int64),
                ("MaxUsn", ctypes.c_int64),
                ("MaximumSize", ctypes.c_uint64),
                ("AllocationDelta", ctypes.c_uint64)]


def _u16(b): return int.from_bytes(bytes(b[:2]), "little")
def _u32(b): return int.from_bytes(bytes(b[:4]), "little")
def _u64(b): return int.from_bytes(bytes(b[:8]), "little")


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin():
    if getattr(sys, "frozen", False):
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, None, None, 1)
    else:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1)
    return int(rc) > 32


def _fixed_ntfs_drives():
    drives = []
    buf = ctypes.create_unicode_buffer(256)
    _k32.GetLogicalDriveStringsW(256, buf)
    for s in "".join(buf).split("\x00"):
        if len(s) == 3 and s[1] == ":":
            try:
                if _k32.GetDriveTypeW(s) != 3:  # DRIVE_FIXED
                    continue
                fs = ctypes.create_unicode_buffer(32)
                if _k32.GetVolumeInformationW(s, None, 0, None, None, None, fs, 32):
                    if fs.value.upper() == "NTFS":
                        drives.append(s[0].upper())
            except Exception:
                continue
    return drives


def _open_volume(letter):
    h = _k32.CreateFileW(f"\\\\.\\{letter}:", 0x80000000, 3, None, 3, 0, None)
    if h == wintypes.HANDLE(-1).value:
        raise OSError(S("vol_open_fail", L=letter))
    return h


def _parse_usn_buffer(buf, n):
    """Returns (records, next_usn). record = dict(frn, parent, ts, reason, attrs, name).
    Handles USN_RECORD_V2 and USN_RECORD_V3 (latter uses low 64 bits of 128-bit IDs)."""
    recs = []
    if n <= 8:
        return recs, _u64(buf[0:8]) if n >= 8 else 0
    nxt = _u64(buf[0:8])
    o = 8
    while o + 8 <= n:
        rec_len = _u32(buf[o:o + 4])
        if rec_len < 60 or o + rec_len > n:
            break
        major = _u16(buf[o + 4:o + 6])
        if major == 2 and rec_len >= 60:
            frn, parent = _u64(buf[o + 8:o + 16]), _u64(buf[o + 16:o + 24])
            ts, reason = _u64(buf[o + 32:o + 40]), _u32(buf[o + 40:o + 44])
            attrs = _u32(buf[o + 52:o + 56])
            fn_len, fn_off = _u16(buf[o + 56:o + 58]), _u16(buf[o + 58:o + 60])
        elif major == 3 and rec_len >= 76:
            frn, parent = _u64(buf[o + 8:o + 16]), _u64(buf[o + 24:o + 32])
            ts, reason = _u64(buf[o + 48:o + 56]), _u32(buf[o + 56:o + 60])
            attrs = _u32(buf[o + 68:o + 72])
            fn_len, fn_off = _u16(buf[o + 72:o + 74]), _u16(buf[o + 74:o + 76])
        else:
            o += rec_len
            continue
        try:
            name = bytes(buf[o + fn_off:o + fn_off + fn_len]).decode("utf-16-le")
        except Exception:
            name = "?"
        if major == 2:
            fid = (frn, 0)
            pid = (parent, 0)
        else:
            # V3: full 128-bit IDs (high halves are 0 for plain NTFS files)
            fid = (_u64(buf[o + 8:o + 16]), _u64(buf[o + 16:o + 24]))
            pid = (_u64(buf[o + 24:o + 32]), _u64(buf[o + 32:o + 40]))
        recs.append({"frn": frn, "parent": parent, "ts": ts,
                     "reason": reason, "attrs": attrs, "name": name,
                     "fid": fid, "pid": pid})
        o += rec_len
    return recs, nxt


def _query_journal(h, letter):
    jd = _UsnJournalData()
    ret = wintypes.DWORD(0)
    ok = _k32.DeviceIoControl(h, FSCTL_QUERY_USN_JOURNAL, None, 0,
                              ctypes.byref(jd), ctypes.sizeof(jd),
                              ctypes.byref(ret), None)
    if not ok:
        raise OSError(S("vol_no_usn", L=letter))
    return jd


def _scan_volume_usn(letter, progress=None):
    """Returns list of dicts(name, deleted, path, drive, is_dir) for one volume."""
    h = _open_volume(letter)
    try:
        _query_journal(h, letter)  # check journal exists
        out = ctypes.create_string_buffer(1024 * 1024)
        ret = wintypes.DWORD(0)
        # 1) ID -> (parent ID, name) maps of current DIRECTORIES only.
        # Ancestors of any path are always dirs, so this is enough and
        # much faster (dirs are a small fraction of all files).
        frn_map = {}
        low_map = {}
        enum_in = _MFTEnumData(0, 0, 0x7FFFFFFFFFFFFFFF, 2, 4)
        total = 0
        while True:
            ok = _k32.DeviceIoControl(h, FSCTL_ENUM_USN_DATA, ctypes.byref(enum_in),
                                      ctypes.sizeof(enum_in), out, len(out),
                                      ctypes.byref(ret), None)
            if not ok:
                if _k32.GetLastError() == ERROR_HANDLE_EOF:
                    break
                raise OSError(S("vol_mft_err", L=letter))
            n = ret.value
            recs, nxt = _parse_usn_buffer(out, n)
            if not recs:
                break
            for r in recs:
                if r["attrs"] & ATTR_DIRECTORY:
                    frn_map[r["fid"]] = (r["pid"], r["name"])
                    low_map[r["fid"][0]] = (r["pid"], r["name"])
            total += len(recs)
            enum_in.StartFileReferenceNumber = nxt
            if progress:
                progress(S("map_progress", L=letter, n=total))
        # 2) deletion records from the journal.
        # The journal wraps quickly on busy systems, so re-query it right
        # before reading and retry once from fresh state on failure.
        found = {}
        for attempt in (1, 2):
            jd = _query_journal(h, letter)
            read_in = _ReadUsnData(jd.FirstUsn, USN_REASON_FILE_DELETE, 0, 0, 0,
                                   jd.UsnJournalID)
            end_usn = jd.NextUsn
            guard = 0
            failed = False
            while guard < 20000:
                guard += 1
                ok = _k32.DeviceIoControl(h, FSCTL_READ_USN_JOURNAL, ctypes.byref(read_in),
                                          ctypes.sizeof(read_in), out, len(out),
                                          ctypes.byref(ret), None)
                if not ok:
                    if _k32.GetLastError() == ERROR_HANDLE_EOF:
                        break
                    if attempt == 1:
                        failed = True
                        break  # retry with a fresh query
                    raise OSError(S("vol_journal_err", L=letter))
                n = ret.value
                recs, nxt = _parse_usn_buffer(out, n)
                if not recs:
                    break
                for r in recs:
                    if r["reason"] & USN_REASON_FILE_DELETE:
                        key = (r["parent"], r["name"])
                        prev = found.get(key)
                        if prev is None or r["ts"] > prev["ts"]:
                            found[key] = r
                read_in.StartUsn = nxt
                if progress:
                    progress(S("journal_progress", L=letter, n=len(found)))
                if nxt >= end_usn:
                    break
            if not failed:
                break
        # 3) resolve full paths
        def lookup(fid):
            ent = frn_map.get(fid)
            if ent is None:
                ent = low_map.get(fid[0])
            return ent

        items = []
        for (parent, name), r in found.items():
            parts = [name]
            cur, broken = r["pid"], False
            seen = {r["fid"]}
            while _frn_index(cur[0]) not in (0, 5) and cur not in seen:
                seen.add(cur)
                ent = lookup(cur)
                if ent is None:
                    broken = True
                    break
                parts.append(ent[1])
                cur = ent[0]
            parts.reverse()
            path = f"{letter}:\\" + "\\".join(parts)
            if broken:
                path = f"{letter}:\\…\\" + "\\".join(parts)
            try:
                dt = filetime_to_local(r["ts"])
            except Exception:
                dt = None
            items.append({"name": name, "deleted": dt, "path": path,
                          "drive": letter + ":", "is_dir": bool(r["attrs"] & ATTR_DIRECTORY)})
        return items
    finally:
        _k32.CloseHandle(h)


def scan_recently_deleted(progress=None):
    """Scan all fixed NTFS volumes. Returns (items, warnings). Needs admin."""
    if not is_admin():
        raise PermissionError(S("scan_perm"))
    items, warnings = [], []
    drives = _fixed_ntfs_drives()
    if not drives:
        warnings.append(S("no_drives"))
    for letter in drives:
        try:
            items += _scan_volume_usn(letter, progress)
        except OSError as e:
            warnings.append(str(e))
    items.sort(key=lambda r: (r["deleted"] is None, r["deleted"]), reverse=True)
    return items[:2000], warnings


# ---------- history DB ----------
def db_init():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS deletions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, path TEXT, watched TEXT,
        size INTEGER, is_dir INTEGER, deleted_at TEXT)""")
    con.commit()
    con.close()


def db_add_many(items):
    """items: list of (name, path, watched, size, is_dir). One transaction."""
    if not items:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.executemany("INSERT INTO deletions(name,path,watched,size,is_dir,deleted_at)"
                    " VALUES(?,?,?,?,?,?)",
                    [(n, p, w, s, d, now) for (n, p, w, s, d) in items])
    con.commit()
    con.close()


def db_list(limit=500):
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT name,path,watched,size,deleted_at FROM deletions"
                       " ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return rows


def db_clear():
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM deletions")
    con.commit()
    con.close()


SCAN_INTERVAL = 3  # seconds between checks


def snapshot_dir(root: Path):
    """Return {str_path: (size, is_dir)}. Fast scandir recursion, no symlink loops."""
    out = {}
    try:
        stack = [str(root)]
        while stack:
            d = stack.pop()
            try:
                with os.scandir(d) as it:
                    for e in it:
                        try:
                            if e.is_symlink():
                                out[e.path] = (-1, 0)
                            elif e.is_dir(follow_symlinks=False):
                                out[e.path] = (-1, 1)
                                stack.append(e.path)
                            else:
                                try:
                                    out[e.path] = (e.stat(follow_symlinks=False).st_size, 0)
                                except OSError:
                                    out[e.path] = (-1, 0)
                        except OSError:
                            continue
            except OSError:
                continue
    except Exception:
        pass
    return out


class Monitor(threading.Thread):
    def __init__(self, on_delete=None, on_status=None):
        super().__init__(daemon=True)
        self.watched: list[str] = []
        self.snaps: dict[str, dict] = {}
        self.on_delete = on_delete
        self.on_status = on_status
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def _set_status(self, text: str):
        if self.on_status:
            try:
                self.on_status(text)
            except Exception:
                pass

    def add(self, path: str):
        # Only registers the path — first scan happens in background,
        # so the UI never freezes even on huge folders.
        path = os.path.normpath(path)
        with self._lock:
            if path not in self.watched:
                self.watched.append(path)

    def watched_list(self):
        with self._lock:
            return list(self.watched)

    def run(self):
        while not self._stop.is_set():
            for w in self.watched_list():
                try:
                    self._set_status(S("status_check", w=w))
                    cur = snapshot_dir(Path(w))
                    with self._lock:
                        old = self.snaps.get(w)
                        self.snaps[w] = cur
                    if old is None:
                        # first scan — just baseline, nothing deleted yet
                        self._set_status(S("status_watching", w=w, n=len(cur)))
                        continue
                    gone = [(os.path.basename(p), p, w, sz, isdir)
                            for p, (sz, isdir) in old.items() if p not in cur]
                    if gone:
                        db_add_many(gone)
                        if self.on_delete:
                            self.on_delete(len(gone))
                    self._set_status(S("status_watching", w=w, n=len(cur)))
                except Exception:
                    pass
            self._stop.wait(SCAN_INTERVAL)

    def stop(self):
        self._stop.set()


# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TrashSpy")
        self.geometry("860x560")
        db_init()
        self._refresh_after = None
        self.usn_items = []
        self.usn_warn = []
        self.monitor = Monitor(
            on_delete=lambda n: self.after(0, self.schedule_refresh),
            on_status=lambda t: self.after(0, lambda: self.scan_label.config(text=t)))
        self.monitor.start()

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.nb = nb

        # language bar
        langbar = ttk.Frame(self)
        langbar.pack(fill="x", padx=8, pady=(0, 6))
        self.lang_label = ttk.Label(langbar, text="")
        self.lang_label.pack(side="left")
        self.lang_combo = ttk.Combobox(langbar, values=NAMES, state="readonly", width=14)
        self.lang_combo.pack(side="left", padx=6)
        try:
            self.lang_combo.set(NAMES[CODES.index(get_lang())])
        except ValueError:
            self.lang_combo.set(NAMES[0])
        self.lang_combo.bind("<<ComboboxSelected>>", self.on_lang_change)

        # Tab 1: history (monitoring)
        f2 = ttk.Frame(nb)
        self.tab_hist = f2
        nb.add(f2, text="")
        self.hist_info = ttk.Label(f2, text="", wraplength=800)
        self.hist_info.pack(anchor="w", pady=4)
        btns = ttk.Frame(f2)
        btns.pack(fill="x")
        self.btn_add_watch = ttk.Button(btns, text="", command=self.add_watch)
        self.btn_add_watch.pack(side="left")
        self.btn_refresh_hist = ttk.Button(btns, text="", command=self.refresh_history)
        self.btn_refresh_hist.pack(side="left", padx=6)
        self.btn_clear_hist = ttk.Button(btns, text="", command=self.clear_history)
        self.btn_clear_hist.pack(side="left")
        self.btn_open_hist = ttk.Button(
            btns, text="", command=lambda: self.open_selected(self.hist_tree))
        self.btn_open_hist.pack(side="left", padx=6)
        self.watch_label = ttk.Label(f2, text="")
        self.watch_label.pack(anchor="w", pady=2)
        self.scan_label = ttk.Label(f2, text="", foreground="gray")
        self.scan_label.pack(anchor="w")
        cols2 = ("name", "deleted", "path", "watched")
        self.hist_tree = ttk.Treeview(f2, columns=cols2, show="headings")
        for c, w in [("name", 200), ("deleted", 150), ("path", 330), ("watched", 170)]:
            self.hist_tree.column(c, width=w)
        self.hist_tree.pack(fill="both", expand=True)
        self.hist_tree.bind("<Double-1>", lambda e: self.open_selected(self.hist_tree))

        # Tab 2: recently deleted (NTFS journal, no monitoring needed)
        f3 = ttk.Frame(nb)
        self.tab_recent = f3
        nb.add(f3, text="")
        self.recent_info = ttk.Label(f3, text="", wraplength=800)
        self.recent_info.pack(anchor="w", pady=4)
        b3 = ttk.Frame(f3)
        b3.pack(fill="x")
        self.btn_scan = ttk.Button(b3, text="", command=self.scan_usn)
        self.btn_scan.pack(side="left")
        self.btn_run_admin = ttk.Button(b3, text="", command=self.run_as_admin)
        self.btn_run_admin.pack(side="left", padx=6)
        self.btn_open_recent = ttk.Button(
            b3, text="", command=lambda: self.open_selected(self.usn_tree))
        self.btn_open_recent.pack(side="left", padx=6)
        self.usn_status = ttk.Label(f3, text="")
        self.usn_status.pack(anchor="w", pady=2)
        srow = ttk.Frame(f3)
        srow.pack(fill="x", pady=(0, 4))
        self.usn_search = ttk.Entry(srow)
        self.usn_search.pack(side="left", fill="x", expand=True)
        self.usn_search.bind("<KeyRelease>", lambda e: self.apply_usn_filter())
        self.usn_search.bind("<FocusIn>", lambda e: self._search_focus(True))
        self.usn_search.bind("<FocusOut>", lambda e: self._search_focus(False))
        self.btn_usn_clear = ttk.Button(srow, text="", command=self.clear_usn_search)
        self.btn_usn_clear.pack(side="left", padx=6)
        cols3 = ("name", "deleted", "path", "drive")
        self.usn_tree = ttk.Treeview(f3, columns=cols3, show="headings")
        for c, w in [("name", 220), ("deleted", 150), ("path", 380), ("drive", 80)]:
            self.usn_tree.column(c, width=w)
        self.usn_tree.pack(fill="both", expand=True)
        self.usn_tree.bind("<Double-1>", lambda e: self.open_selected(self.usn_tree))

        self.apply_language()
        self.refresh_history()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_lang_change(self, event=None):
        try:
            code = CODES[NAMES.index(self.lang_combo.get())]
        except ValueError:
            return
        save_lang(code)
        self.apply_language()

    def _render_watch_label(self):
        watched = self.monitor.watched_list()
        if watched:
            self.watch_label.config(text=S("watch_fmt", x="; ".join(watched)))
        else:
            self.watch_label.config(text=S("watch_none"))

    def apply_language(self):
        self.nb.tab(self.tab_hist, text=S("tab_history"))
        self.nb.tab(self.tab_recent, text=S("tab_recent"))
        self.lang_label.config(text=S("lang_label"))
        self.hist_info.config(text=S("hist_info"))
        self.btn_add_watch.config(text=S("btn_add_watch"))
        self.btn_refresh_hist.config(text=S("btn_refresh"))
        self.btn_clear_hist.config(text=S("btn_clear_hist"))
        self.btn_open_hist.config(text=S("btn_open_folder"))
        self.recent_info.config(text=S("recent_info"))
        self.btn_scan.config(text=S("btn_scan"))
        self.btn_run_admin.config(text=S("btn_run_admin"))
        self.btn_open_recent.config(text=S("btn_open_folder"))
        self.btn_usn_clear.config(text=S("btn_clear"))
        if not self.usn_search.get():
            self.usn_search.insert(0, S("search_ph"))
        for c, key in [("name", "col_name"), ("deleted", "col_deleted"),
                       ("path", "col_path"), ("watched", "col_watched")]:
            self.hist_tree.heading(c, text=S(key))
        for c, key in [("name", "col_name"), ("deleted", "col_deleted"),
                       ("path", "col_path"), ("drive", "col_drive")]:
            self.usn_tree.heading(c, text=S(key))
        self._render_watch_label()

    # --- handlers ---
    def schedule_refresh(self):
        # Debounce: many deletions at once -> single list rebuild, no lag.
        if self._refresh_after is None:
            self._refresh_after = self.after(1500, self._do_refresh)

    def _do_refresh(self):
        self._refresh_after = None
        self.refresh_history()

    def refresh_history(self):
        for i in self.hist_tree.get_children():
            self.hist_tree.delete(i)
        for name, path, watched, size, dt in db_list():
            self.hist_tree.insert("", "end", values=(name, dt, path, watched))

    def add_watch(self):
        d = filedialog.askdirectory(title=S("dlg_choose_dir"))
        if d:
            self.monitor.add(d)
            self._render_watch_label()
            self.scan_label.config(text=S("first_scan"))

    def run_as_admin(self):
        try:
            if restart_as_admin():
                messagebox.showinfo("TrashSpy", S("admin_launched"))
            else:
                messagebox.showerror(S("err_title"), S("err_admin_fail"))
        except Exception as e:
            messagebox.showerror(S("err_title"), str(e))

    def scan_usn(self):
        self.usn_status.config(text=S("scanning"))
        for i in self.usn_tree.get_children():
            self.usn_tree.delete(i)
        th = threading.Thread(target=self._scan_usn_worker, daemon=True)
        th.start()

    def _scan_usn_worker(self):
        try:
            items, warnings = scan_recently_deleted(
                progress=lambda t: self.after(0, lambda: self.usn_status.config(text=t)))
        except PermissionError as e:
            self.after(0, lambda: self.usn_status.config(text=str(e)))
            self.after(0, lambda: messagebox.showwarning(S("need_admin_title"), str(e)))
            return
        except Exception as e:
            self.after(0, lambda: self.usn_status.config(text=f"{S('err_title')}: {e}"))
            return

        def done():
            self.usn_items = items
            self.usn_warn = warnings
            self.apply_usn_filter()
        self.after(0, done)

    def _search_query(self):
        q = self.usn_search.get().strip()
        if not q or q == S("search_ph"):
            return ""
        return q.lower()

    def _search_focus(self, focused):
        if focused:
            if self.usn_search.get() == S("search_ph"):
                self.usn_search.delete(0, "end")
        elif not self.usn_search.get().strip():
            self.usn_search.delete(0, "end")
            self.usn_search.insert(0, S("search_ph"))

    def clear_usn_search(self):
        self.usn_search.delete(0, "end")
        self.usn_search.insert(0, S("search_ph"))
        self.apply_usn_filter()

    def apply_usn_filter(self):
        for i in self.usn_tree.get_children():
            self.usn_tree.delete(i)
        items = getattr(self, "usn_items", [])
        warnings = getattr(self, "usn_warn", [])
        q = self._search_query()
        shown = 0
        for r in items:
            if q and q not in r["name"].lower() and q not in r["path"].lower():
                continue
            dt = r["deleted"].strftime("%Y-%m-%d %H:%M") if r["deleted"] else "?"
            self.usn_tree.insert("", "end", values=(r["name"], dt, r["path"], r["drive"]))
            shown += 1
        msg = S("found_fmt", n=len(items)) + " | " + S("shown_fmt", n=shown)
        if warnings:
            msg += " | " + " | ".join(warnings)
        self.usn_status.config(text=msg)

    def open_selected(self, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("TrashSpy", S("pick_row"))
            return
        vals = tree.item(sel[0], "values")
        if len(vals) < 3:
            return
        self.open_containing(vals[2])

    @staticmethod
    def open_containing(path: str):
        """Open nearest existing parent folder of a (deleted) path in Explorer."""
        d = os.path.dirname(path)
        for _ in range(12):
            if d and os.path.isdir(d):
                os.startfile(d)
                return
            nd = os.path.dirname(d)
            if not nd or nd == d:
                break
            d = nd
        messagebox.showwarning("TrashSpy", S("folder_gone", path=path))

    def clear_history(self):
        if messagebox.askyesno(S("dlg_confirm"), S("ask_clear_hist")):
            db_clear()
            self.refresh_history()

    def on_close(self):
        self.monitor.stop()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
