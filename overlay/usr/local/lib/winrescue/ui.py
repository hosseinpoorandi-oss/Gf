#!/usr/bin/env python3
import subprocess, threading, gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

CORE = "/usr/local/bin/wr-core"
CSS = b"""
window{background:#0b1220;color:#e5e7eb;font-family:"DejaVu Sans";}
.h1{font-size:34px;font-weight:700;} .sub{color:#94a3b8;font-size:15px;}
.card{border-radius:18px;padding:26px;border:1px solid #1f2a44;background:#111a2e;}
.card:hover{background:#17223c;}
.card.danger{border-color:#7f1d1d;} .card.danger:hover{background:#2a1218;}
.card.safe{border-color:#14532d;} .card.safe:hover{background:#0f2a1d;}
.ct{font-size:22px;font-weight:700;} .cd{color:#94a3b8;font-size:14px;}
.btn{border-radius:10px;padding:10px 22px;background:#1e293b;color:#e5e7eb;border:none;}
.btn.red{background:#dc2626;} .btn.green{background:#16a34a;}
.warn{color:#fca5a5;font-size:15px;}
textview,textview text{background:#0a0f1c;color:#cbd5e1;font-family:monospace;font-size:13px;}
"""
TAGS = {"OK": "#4ade80", "WARN": "#fbbf24", "FAIL": "#f87171", "ABNORMAL": "#fbbf24", "INFO": "#94a3b8"}

def lbl(text, cls, wrap=False):
    l = Gtk.Label(label=text); l.get_style_context().add_class(cls); l.set_line_wrap(wrap); return l
def btn(text, cls="", cb=None):
    b = Gtk.Button(label=text); sc = b.get_style_context(); sc.add_class("btn")
    if cls: sc.add_class(cls)
    if cb: b.connect("clicked", cb)
    return b

class App(Gtk.Window):
    def __init__(s):
        super().__init__(title="WinRescue"); s.fullscreen()
        p = Gtk.CssProvider(); p.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        s.sel = None; s.flags = set(); s.cd_id = None
        s.stack = Gtk.Stack(); s.add(s.stack)
        s.stack.add_named(s.home(), "home"); s.stack.add_named(s.wipe_page(), "wipe"); s.stack.add_named(s.log_page(), "log")
        s.show_all(); s.cd_box.hide(); s.back.hide()

    def go(s, name): s.stack.set_visible_child_name(name)

    def card(s, title, desc, cls, cb):
        b = Gtk.Button(); b.get_style_context().add_class("card"); b.get_style_context().add_class(cls)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        t = lbl(title, "ct"); d = lbl(desc, "cd", True); d.set_max_width_chars(34)
        t.set_xalign(0); d.set_xalign(0); v.pack_start(t, 0, 0, 0); v.pack_start(d, 0, 0, 0)
        b.add(v); b.set_size_request(400, 190); b.connect("clicked", cb); return b

    def home(s):
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        v.pack_start(lbl("WinRescue", "h1"), 0, 0, 0)
        v.pack_start(lbl("Runs from this USB drive. Nothing is installed on your PC.", "sub"), 0, 0, 0)
        row = Gtk.Box(spacing=24, halign=Gtk.Align.CENTER)
        row.pack_start(s.card("Full Windows Wipe", "Erase Windows, C:, EFI, MSR and Recovery. Disk becomes unallocated, then reboots to BIOS.", "danger", lambda b: s.open_wipe()), 0, 0, 0)
        row.pack_start(s.card("Smart Windows Repair", "Check system files and registry, fix boot files, clean junk, then boot Windows.", "safe", lambda b: s.repair()), 0, 0, 0)
        v.pack_start(row, 0, 0, 0); return v

    # ---- wipe ----
    def wipe_page(s):
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        v.pack_start(lbl("Full Windows Wipe", "h1"), 0, 0, 0)
        w = lbl("The WHOLE selected disk will be erased: every partition and every file. This cannot be undone.", "warn", True)
        w.set_max_width_chars(60); v.pack_start(w, 0, 0, 0)
        s.disk_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); v.pack_start(s.disk_box, 0, 0, 0)
        s.entry = Gtk.Entry(placeholder_text="Type WIPE to confirm"); s.entry.connect("changed", s.check); v.pack_start(s.entry, 0, 0, 0)
        row = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        s.go_btn = btn("Erase disk", "red", s.do_wipe); s.go_btn.set_sensitive(False)
        row.pack_start(btn("Back", "", lambda b: s.go("home")), 0, 0, 0); row.pack_start(s.go_btn, 0, 0, 0)
        v.pack_start(row, 0, 0, 0); return v

    def open_wipe(s):
        for c in s.disk_box.get_children(): c.destroy()
        s.sel = None; s.entry.set_text(""); grp = None
        out = subprocess.run([CORE, "disks"], capture_output=True, text=True).stdout.strip().splitlines()
        for line in out:
            n, size, model, win = line.split("\t")
            r = Gtk.RadioButton.new_with_label_from_widget(grp, f"/dev/{n}   {size}   {model}" + ("   [Windows found]" if win == "windows" else ""))
            grp = grp or r; r.connect("toggled", s.pick, n); s.disk_box.pack_start(r, 0, 0, 0)
        if not out: s.disk_box.pack_start(lbl("No disks found.", "sub"), 0, 0, 0)
        s.disk_box.show_all(); s.check(); s.go("wipe")

    def pick(s, b, n):
        if b.get_active(): s.sel = n; s.check()
    def check(s, *a): s.go_btn.set_sensitive(bool(s.sel) and s.entry.get_text().strip() == "WIPE")
    def do_wipe(s, b):
        s.job(f"Erasing /dev/{s.sel}", ["wipe", s.sel],
              lambda rc: rc == 0 and s.countdown("Disk is clean. Rebooting to BIOS/UEFI setup (on legacy BIOS, press your setup key at power-on)", "reboot-fw"))

    # ---- repair ----
    def repair(s): s.job("Smart Windows Repair", ["repair"], s.after_repair)
    def after_repair(s, rc):
        if rc != 0: return
        if "ABNORMAL" in s.flags:
            d = Gtk.MessageDialog(transient_for=s, modal=True, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO,
                                  text="Your C drive size looks abnormal. Do you want to remove unnecessary files? (Yes / No)")
            r = d.run(); d.destroy()
            if r == Gtk.ResponseType.YES:
                s.job("Cleaning unnecessary files", ["clean"], lambda rc: s.to_windows()); return
        s.to_windows()
    def to_windows(s):
        s.countdown("Repair complete. Remove the USB drive now. Rebooting into Windows", "finish")

    # ---- log/job ----
    def log_page(s):
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); v.set_border_width(40)
        top = Gtk.Box(spacing=12); s.title = lbl("", "h1"); s.spin = Gtk.Spinner()
        top.pack_start(s.title, 0, 0, 0); top.pack_start(s.spin, 0, 0, 0); v.pack_start(top, 0, 0, 0)
        s.buf = Gtk.TextBuffer()
        for k, c in TAGS.items(): s.buf.create_tag(k, foreground=c)
        s.view = Gtk.TextView(buffer=s.buf, editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD)
        sw = Gtk.ScrolledWindow(); sw.add(s.view); v.pack_start(sw, 1, 1, 0)
        s.cd_box = Gtk.Box(spacing=12); s.cd_lbl = lbl("", "sub"); s.cd_box.pack_start(s.cd_lbl, 0, 0, 0)
        s.cd_box.pack_start(btn("Cancel", "", s.cancel_cd), 0, 0, 0); v.pack_start(s.cd_box, 0, 0, 0)
        s.back = btn("Back to menu", "", lambda b: s.go("home")); v.pack_start(s.back, 0, 0, 0); return v

    def job(s, title, args, done):
        s.title.set_text(title); s.buf.set_text(""); s.flags = set(); s.back.hide(); s.cd_box.hide(); s.spin.start(); s.go("log")
        def work():
            p = subprocess.Popen([CORE] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in p.stdout: GLib.idle_add(s.add, line.rstrip())
            p.wait(); GLib.idle_add(s.finished, p.returncode, done)
        threading.Thread(target=work, daemon=True).start()
    def add(s, l):
        tag = l.split(" ", 1)[0]
        if tag == "ABNORMAL": s.flags.add(tag)
        it = s.buf.get_end_iter()
        if tag in TAGS: s.buf.insert_with_tags_by_name(it, l + "\n", tag)
        else: s.buf.insert(it, l + "\n")
        m = s.buf.create_mark(None, s.buf.get_end_iter(), False); s.view.scroll_to_mark(m, 0, False, 0, 0); s.buf.delete_mark(m)
    def finished(s, rc, done):
        s.spin.stop(); s.back.show()
        if rc != 0: s.add("FAIL Operation did not complete.")
        done(rc)

    def countdown(s, text, cmd, n=10):
        s.cd_n = n; s.cd_text = text; s.cd_cmd = cmd; s.cd_box.show_all()
        def tick():
            if s.cd_n <= 0: subprocess.Popen([CORE, s.cd_cmd]); return False
            s.cd_lbl.set_text(f"{s.cd_text} in {s.cd_n}s..."); s.cd_n -= 1; return True
        tick(); s.cd_id = GLib.timeout_add_seconds(1, tick)
    def cancel_cd(s, b):
        if s.cd_id: GLib.source_remove(s.cd_id); s.cd_id = None
        s.cd_box.hide()

App().connect("destroy", Gtk.main_quit); Gtk.main()
