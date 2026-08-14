#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""המביא לדפוס - Virtual Printer | v1.2"""

import sys, os
from pathlib import Path

if sys.platform == "win32":
    import subprocess as _sp
    _HIDE = 0x08000000
    _ro, _rp = _sp.run, _sp.Popen
    def _rh(*a,**kw): kw.setdefault("creationflags",_HIDE); return _ro(*a,**kw)
    def _ph(*a,**kw): kw.setdefault("creationflags",_HIDE); return _rp(*a,**kw)
    _sp.run=_rh; _sp.Popen=_ph

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QFileDialog,
    QDialog, QComboBox, QMessageBox, QSizePolicy,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher
from PyQt6.QtGui  import (
    QFont, QDragEnterEvent, QDropEvent, QKeySequence,
    QShortcut, QPixmap, QColor, QIcon, QPainter, QPainterPath, QBrush
)

from settings_manager import SettingsManager
from print_engine      import PrintEngine
from ui_components     import (
    OptionCard, ToggleSwitch, DateTimeWidget,
    SettingsPanel, PasswordDialog
)

APP_NAME    = "המביא לדפוס"
APP_NAME_EN = "The Print Bringer"
VERSION     = "1.2"


def make_app_icon():
    """Create printer icon pixmap for tray."""
    pix = QPixmap(64,64); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Green rounded rect background
    p.setBrush(QBrush(QColor("#4a7c59"))); p.setPen(Qt.PenStyle.NoPen)
    path = QPainterPath(); path.addRoundedRect(0,0,64,64,12,12); p.drawPath(path)
    # Printer body
    p.setBrush(QBrush(QColor("#ffffff"))); p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(12,22,40,22,4,4)
    # Paper top
    p.drawRoundedRect(18,12,28,14,2,2)
    # Paper out
    p.drawRoundedRect(18,36,28,16,2,2)
    # Dot
    p.setBrush(QBrush(QColor("#4a7c59"))); p.drawEllipse(38,28,6,6)
    p.end()
    return QIcon(pix)


class VirtualPrinterApp(QMainWindow):
    def __init__(self, file_to_print=None):
        super().__init__()
        self.settings     = SettingsManager()
        self.print_engine = PrintEngine(self.settings)
        self.lang         = self.settings.get("language","he")
        self.dark_mode    = self.settings.get("dark_mode",False)
        self.sel_opt      = 0
        self.cur_file     = file_to_print
        self.copies       = 1
        self.tog_states   = {}
        self._opt_offset  = 0

        self.setAcceptDrops(True)
        self._app_icon = make_app_icon()
        self.setWindowIcon(self._app_icon)

        self._setup_window()
        self._apply_theme()
        self._build_ui()
        self._setup_shortcut()
        self._setup_tray()
        self._start_clock()
        self._start_file_watcher()

        if file_to_print:
            self.load_file(file_to_print)

        # Fix #3: first-run check
        if self.settings.get("first_run", True):
            self.settings.set("first_run", False); self.settings.save()
            QTimer.singleShot(800, self._check_printer_first_run)

    # ── Window ────────────────────────────────────────────────────────────
    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME if self.lang=='he' else APP_NAME_EN}  v{VERSION}")
        self.setMinimumSize(860,660); self.resize(920,700)
        scr = QApplication.primaryScreen().geometry()
        self.move((scr.width()-920)//2, (scr.height()-700)//2)

    def _apply_theme(self):
        self.setStyleSheet(DARK_SS if self.dark_mode else LIGHT_SS)

    # ── First-run check ───────────────────────────────────────────────────
    def _check_printer_first_run(self):
        from install_printer import is_installed
        if not is_installed():
            msg = QMessageBox(self)
            msg.setWindowTitle(self.T("המביא לדפוס","The Print Bringer"))
            msg.setText(self.T(
                "המדפסת הווירטואלית 'המביא לדפוס' עדיין לא מותקנת.\n\n"
                "האם להתקין אותה עכשיו?\n\n"
                "(תמיד ניתן להתקין דרך הגדרות → התקנה)",
                "The virtual printer 'המביא לדפוס' is not installed.\n\n"
                "Install it now?\n\n"
                "(You can always install via Settings → Installation)"
            ))
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            if msg.exec() == QMessageBox.StandardButton.Yes:
                self._open_settings_install_tab()

    def _open_settings_install_tab(self):
        try:
            dlg = SettingsPanel(self, self.settings, self.lang, self.dark_mode, open_tab="install")
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.settings.save(); self._full_rebuild()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ── Build UI ──────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        vbox = QVBoxLayout(root); vbox.setContentsMargins(0,0,0,0); vbox.setSpacing(0)
        vbox.addWidget(self._build_titlebar())

        body = QWidget(); body.setObjectName("body")
        bl   = QVBoxLayout(body); bl.setContentsMargins(24,18,24,18); bl.setSpacing(14)
        bl.addWidget(self._build_file_bar())
        bl.addWidget(self._lbl(self.T("אפשרויות הדפסה מהירה","Quick Print Options"),"sectionLabel"))
        bl.addWidget(self._build_options_nav())
        bl.addWidget(self._lbl(self.T("הגדרות הדפסה","Print Settings"),"sectionLabel"))

        self._tog_wrap = QWidget()
        self._tog_row  = QHBoxLayout(self._tog_wrap)
        self._tog_row.setContentsMargins(0,0,0,0); self._tog_row.setSpacing(8)
        self._tog_row.addStretch()
        bl.addWidget(self._tog_wrap)
        self._rebuild_toggles()

        # Printer + copies
        self._printer_section = QWidget()
        ps = QHBoxLayout(self._printer_section)
        ps.setContentsMargins(0,0,0,0); ps.setSpacing(14)
        pc = QVBoxLayout()
        self._printer_lbl   = self._lbl(self.T("מדפסת","Printer"),"ctrlLbl")
        self._printer_combo = QComboBox(); self._printer_combo.setObjectName("printerCombo")
        self._printer_combo.setMinimumWidth(240)
        pc.addWidget(self._printer_lbl); pc.addWidget(self._printer_combo); ps.addLayout(pc)
        cc = QVBoxLayout()
        self._copies_lbl = self._lbl(self.T("עותקים","Copies"),"ctrlLbl")
        cr = QHBoxLayout(); cr.setSpacing(4)
        self._btn_m = QPushButton("−"); self._btn_m.setObjectName("copiesBtn"); self._btn_m.setFixedSize(32,32); self._btn_m.clicked.connect(lambda: self._chg_copies(-1))
        self._copies_disp = QLabel("1"); self._copies_disp.setObjectName("copiesCount"); self._copies_disp.setAlignment(Qt.AlignmentFlag.AlignCenter); self._copies_disp.setFixedWidth(40)
        self._btn_p = QPushButton("+"); self._btn_p.setObjectName("copiesBtn"); self._btn_p.setFixedSize(32,32); self._btn_p.clicked.connect(lambda: self._chg_copies(1))
        cr.addWidget(self._btn_m); cr.addWidget(self._copies_disp); cr.addWidget(self._btn_p)
        cc.addWidget(self._copies_lbl); cc.addLayout(cr)
        ps.addLayout(cc); ps.addStretch()
        bl.addWidget(self._printer_section); bl.addStretch()

        ar = QHBoxLayout(); ar.setSpacing(10)
        self._btn_print = QPushButton("🖨️  "+self.T("הדפס עכשיו","Print Now"))
        self._btn_print.setObjectName("btnPrimary"); self._btn_print.setMinimumHeight(50); self._btn_print.clicked.connect(self._do_print)
        self._btn_prev = QPushButton(self.T("תצוגה מקדימה","Preview"))
        self._btn_prev.setObjectName("btnSecondary"); self._btn_prev.setMinimumHeight(50); self._btn_prev.clicked.connect(self._do_preview)
        ar.addWidget(self._btn_print,2); ar.addWidget(self._btn_prev,1)
        bl.addLayout(ar)
        vbox.addWidget(body)

        self._reload_printers(); self._apply_printer_visibility(); self._update_dir()
        self._start_printer_status_timer()

    def _start_printer_status_timer(self):
        """
        זיהוי יציב ואמין של המדפסת הווירטואלית: בדיקה תקופתית שהדרייבר
        עדיין מותקן, ועדכון סטטוס בשורת הכותרת / מגש המערכת.
        """
        self._printer_status_ok = None
        self._status_timer = QTimer()
        self._status_timer.setInterval(30000)
        self._status_timer.timeout.connect(self._check_printer_status)
        self._status_timer.start()
        QTimer.singleShot(2000, self._check_printer_status)

    def _check_printer_status(self):
        from install_printer import is_installed
        try:
            ok = is_installed()
        except Exception:
            ok = False
        if ok != self._printer_status_ok:
            self._printer_status_ok = ok
            if ok:
                self._tray.setToolTip(APP_NAME)
            else:
                self._tray.setToolTip(APP_NAME + " — " + self.T(
                    "המדפסת הווירטואלית לא מותקנת",
                    "Virtual printer not installed"))
                self._tray.showMessage(
                    APP_NAME,
                    self.T("המדפסת הווירטואלית אינה מותקנת. פתח הגדרות → התקנה.",
                           "Virtual printer is not installed. Open Settings → Install."),
                    QSystemTrayIcon.MessageIcon.Warning, 6000)

    # ── Fix #10: Title bar — version starts under left edge of app name ───
    def _build_titlebar(self):
        bar = QWidget(); bar.setObjectName("titleBar"); bar.setFixedHeight(68)
        h = QHBoxLayout(bar); h.setContentsMargins(18,0,14,0); h.setSpacing(0)

        # RIGHT: icon + name/version block
        rs = QHBoxLayout(); rs.setSpacing(8); rs.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        ico = QLabel(); ico.setPixmap(self._app_icon.pixmap(36,36))
        ico.setObjectName("plainLbl"); ico.setFixedSize(40,40)
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Name + version: left-aligned column
        nv = QVBoxLayout(); nv.setSpacing(0); nv.setContentsMargins(0,0,0,0)
        nv.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._title_lbl = QLabel(APP_NAME if self.lang=="he" else APP_NAME_EN)
        self._title_lbl.setObjectName("appTitle")
        self._ver_lbl   = QLabel(f"v{VERSION}"); self._ver_lbl.setObjectName("verLabel")
        # Fix #10: align version to LEFT (starts under beginning of name)
        self._ver_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        nv.addWidget(self._title_lbl); nv.addWidget(self._ver_lbl)
        rs.addWidget(ico); rs.addLayout(nv); rs.addStretch()

        # CENTER: date/time
        self._dt = DateTimeWidget(self.lang, self.settings)

        # LEFT: controls
        ls = QHBoxLayout(); ls.setSpacing(6); ls.addStretch()
        self._lang_frame = QFrame(); self._lang_frame.setObjectName("langFrame"); self._lang_frame.setFixedHeight(32)
        lf = QHBoxLayout(self._lang_frame); lf.setContentsMargins(2,2,2,2); lf.setSpacing(0)
        self._btn_he = QPushButton("עב"); self._btn_he.setFixedSize(36,28)
        self._btn_en = QPushButton("EN"); self._btn_en.setFixedSize(36,28)
        self._btn_he.clicked.connect(lambda: self._set_lang("he"))
        self._btn_en.clicked.connect(lambda: self._set_lang("en"))
        lf.addWidget(self._btn_he); lf.addWidget(self._btn_en); self._refresh_lang_btns()
        self._dark_btn = QPushButton("🌙" if not self.dark_mode else "☀️")
        self._dark_btn.setObjectName("iconBtn"); self._dark_btn.setFixedSize(32,32); self._dark_btn.clicked.connect(self._toggle_dark)
        self._cfg_btn = QPushButton("⚙️"); self._cfg_btn.setObjectName("iconBtn"); self._cfg_btn.setFixedSize(32,32); self._cfg_btn.clicked.connect(self._open_settings)
        ls.addWidget(self._lang_frame); ls.addWidget(self._dark_btn); ls.addWidget(self._cfg_btn)
        h.addLayout(rs,1); h.addWidget(self._dt,0,Qt.AlignmentFlag.AlignCenter); h.addLayout(ls,1)
        return bar

    def _refresh_lang_btns(self):
        for btn,lang in ((self._btn_he,"he"),(self._btn_en,"en")):
            n="langSegActive" if self.lang==lang else "langSegInactive"
            btn.setObjectName(n); btn.style().unpolish(btn); btn.style().polish(btn)

    def _build_file_bar(self):
        bar = QFrame(); bar.setObjectName("fileBar")
        h = QHBoxLayout(bar); h.setContentsMargins(16,12,16,12); h.setSpacing(12)
        self._file_ico = QLabel("📄"); self._file_ico.setFont(QFont("Segoe UI Emoji",24)); self._file_ico.setObjectName("plainLbl"); h.addWidget(self._file_ico)
        det = QVBoxLayout(); det.setSpacing(2)
        self._file_name = QLabel(self.T("גרור קובץ לכאן או לחץ לבחירה","Drag file here or click to choose")); self._file_name.setObjectName("fileName")
        self._file_meta = QLabel(self.T("אין קובץ נבחר","No file selected")); self._file_meta.setObjectName("fileMeta")
        det.addWidget(self._file_name); det.addWidget(self._file_meta); h.addLayout(det,1)
        self._choose_btn = QPushButton(self.T("📂  בחר קובץ","📂  Choose File")); self._choose_btn.setObjectName("btnSecondary"); self._choose_btn.setFixedHeight(36); self._choose_btn.clicked.connect(self._choose_file); h.addWidget(self._choose_btn)
        self._pages_badge = QLabel(""); self._pages_badge.setObjectName("pagesBadge"); self._pages_badge.hide(); h.addWidget(self._pages_badge)
        bar.setCursor(Qt.CursorShape.PointingHandCursor); bar.mousePressEvent=lambda e:self._choose_file()
        return bar

    def _build_options_nav(self):
        wrapper = QWidget(); wrapper.setObjectName("optNavWrapper")
        wrapper.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        h = QHBoxLayout(wrapper); h.setContentsMargins(0,0,0,0); h.setSpacing(4)
        self._nav_left  = QPushButton("❮"); self._nav_left.setObjectName("navArrow"); self._nav_left.setFixedSize(28,170); self._nav_left.clicked.connect(lambda: self._scroll_opts(-1))
        self._opt_clip  = QWidget(); self._opt_clip.setObjectName("optClip"); self._opt_clip.setFixedHeight(180); self._opt_clip.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed); self._opt_clip.setStyleSheet("background:transparent;")
        self._opt_inner = QWidget(self._opt_clip); self._opt_inner.setObjectName("optInner"); self._opt_inner.setStyleSheet("background:transparent;")
        self._nav_right = QPushButton("❯"); self._nav_right.setObjectName("navArrow"); self._nav_right.setFixedSize(28,170); self._nav_right.clicked.connect(lambda: self._scroll_opts(1))
        h.addWidget(self._nav_left); h.addWidget(self._opt_clip,1); h.addWidget(self._nav_right)
        self._opt_cards=[]; self._opt_offset=0; self._rebuild_options_inner()
        return wrapper

    def _rebuild_options_inner(self):
        for c in self._opt_cards: c.setParent(None); c.deleteLater()
        self._opt_cards=[]; CARD_W=154; GAP=10; x=0
        vis=[o for o in self.settings.get_options() if o.get("visible",True)]
        all_o=self.settings.get_options()
        for opt in vis:
            ri=next((i for i,o in enumerate(all_o) if o.get("id")==opt.get("id")),0)
            card=OptionCard(opt,ri==self.sel_opt,self.lang,self.dark_mode)
            card.setParent(self._opt_inner); card.clicked_signal.connect(lambda ri_=ri:self._sel_option(ri_))
            card.move(x,0); card.show(); self._opt_cards.append(card); x+=CARD_W+GAP
        self._opt_inner.setFixedSize(max(x,1),180); self._apply_opt_offset()

    def _apply_opt_offset(self):
        CARD_W=154; GAP=10
        clip_w=self._opt_clip.width() or 600
        n=len([o for o in self.settings.get_options() if o.get("visible",True)])
        total=n*(CARD_W+GAP); max_off=max(0,total-clip_w)
        self._opt_offset=max(0,min(self._opt_offset,max_off))
        self._opt_inner.move(-self._opt_offset,0)
        self._nav_left.setVisible(self._opt_offset>0)
        self._nav_right.setVisible(self._opt_offset<max_off)

    def _scroll_opts(self,d): self._opt_offset+=d*164; self._apply_opt_offset()

    def resizeEvent(self,e):
        super().resizeEvent(e)
        if hasattr(self,'_opt_clip'): self._apply_opt_offset()

    # ── Fix #12: Toggles direction ────────────────────────────────────────
    def _rebuild_toggles(self):
        while self._tog_row.count():
            item=self._tog_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        opts=self.settings.get_options()
        tids=opts[self.sel_opt].get("toggles",[]) if self.sel_opt<len(opts) else []
        all_t=self.settings.get_toggles(); show=[t for t in all_t if t["id"] in tids] if tids else all_t

        self.tog_states={}; self._tog_widgets={}
        is_rtl = (self.lang=="he")

        for tog in show:
            w=QWidget(); w.setObjectName("togItem")
            cl=QHBoxLayout(w); cl.setContentsMargins(0,2,12,2); cl.setSpacing(6)
            name=tog.get("name_he" if self.lang=="he" else "name_en",tog.get("name_he",""))
            sw=ToggleSwitch(); sw.setChecked(False)
            sw.toggled.connect(lambda v,tid=tog["id"]:self.tog_states.update({tid:v}))
            self.tog_states[tog["id"]]=False; self._tog_widgets[tog["id"]]=sw
            lbl=QLabel(name); lbl.setObjectName("togLabel")

            if is_rtl:
                # RTL: label first, then switch (so visually switch is on right in RTL layout)
                cl.addWidget(lbl); cl.addWidget(sw)
            else:
                cl.addWidget(sw); cl.addWidget(lbl)

            self._tog_row.insertWidget(self._tog_row.count(),w)
        self._tog_row.addStretch()

    def _reload_printers(self):
        self._printer_combo.blockSignals(True); self._printer_combo.clear()
        self._printers=PrintEngine.get_system_printers()
        for p in self._printers: self._printer_combo.addItem(p)
        default=self.settings.get("default_printer","")
        if default and default in self._printers: self._printer_combo.setCurrentText(default); self._sel_printer=default
        elif self._printers: self._printer_combo.setCurrentIndex(0); self._sel_printer=self._printers[0]
        else: self._sel_printer=""
        self._printer_combo.currentIndexChanged.connect(self._on_printer_changed)
        self._printer_combo.blockSignals(False)

    def _on_printer_changed(self,idx):
        if 0<=idx<len(self._printers): self._sel_printer=self._printers[idx]

    def _apply_printer_visibility(self):
        self._printer_section.setVisible(self.settings.get("show_printer_selector",True))

    def _apply_cfg_btn_visibility(self):
        self._cfg_btn.setVisible(self.settings.get("show_settings_btn",True))

    def _setup_shortcut(self):
        self._sh=None; self._update_shortcut()

    def _update_shortcut(self):
        if self._sh: self._sh.setEnabled(False); self._sh.deleteLater(); self._sh=None
        key=self.settings.get("settings_shortcut","F8")
        try: self._sh=QShortcut(QKeySequence(key),self); self._sh.activated.connect(self._open_settings)
        except: pass

    # ── Fix #9: System tray with proper icon + tooltip + menu ─────────────
    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self._app_icon, self)
        self._tray.setToolTip(APP_NAME)   # Fix #9: tooltip = app name
        menu = QMenu()

        # Fix #9: first item = app name (non-clickable header style)
        header = menu.addAction(APP_NAME)
        header.setEnabled(False)
        f = header.font(); f.setBold(True); header.setFont(f)
        menu.addSeparator()

        menu.addAction(self.T("פתח","Open"), self.show)
        menu.addAction(self.T("הגדרות","Settings"), self._open_settings)
        menu.addSeparator()

        # Fix #9: "About" at end of menu
        menu.addAction(self.T("אודות","About"), self._show_about)
        menu.addAction(self.T("יציאה","Exit"), QApplication.quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda r: self.show() if r==QSystemTrayIcon.ActivationReason.DoubleClick else None
        )
        self._tray.show()

    def _show_about(self):
        QMessageBox.about(self, self.T("אודות","About"),
            f"<b>{APP_NAME}</b><br>v{VERSION}<br><br>"
            + self.T("מדפסת וירטואלית חכמה לWindows","Smart virtual printer for Windows"))

    def closeEvent(self,event):
        event.ignore(); self.hide()
        self._tray.showMessage(APP_NAME, self.T("פועל ברקע","Running in background"),
                               QSystemTrayIcon.MessageIcon.Information, 2000)

    def _start_file_watcher(self):
        from printer_installer import PrinterInstaller
        d=PrinterInstaller.get_output_dir(); d.mkdir(parents=True,exist_ok=True)
        self._watcher=QFileSystemWatcher(); self._watcher.addPath(str(d))
        self._watcher.directoryChanged.connect(self._on_print_job)
        # Debounce: מחכה שהקובץ יסיים להיכתב לפני העיבוד
        self._job_debounce=QTimer(); self._job_debounce.setSingleShot(True)
        self._job_debounce.setInterval(350)
        self._job_debounce.timeout.connect(self._process_incoming_job)

    def _on_print_job(self,path):
        self._job_debounce.start()

    def _process_incoming_job(self):
        """
        טיפול יציב בקובץ שנקלט מהמדפסת הווירטואלית:
        1. מחכה עד שגודל job.pdf יציב (הכתיבה הסתיימה) — עד 3 שניות.
        2. משנה את שמו לשם ייחודי (rename אטומי) — כך הדפסה הבאה
           לא תדרוס את הקובץ הנוכחי.
        העיבוד מתבצע מחוץ לחוט ה-GUI.
        """
        import time as _t, uuid
        from printer_installer import PrinterInstaller
        d = PrinterInstaller.get_output_dir()
        src = d / "job.pdf"
        if not src.exists():
            return

        def _size():
            try: return src.stat().st_size
            except Exception: return -1

        # ── המתנה ליציבות הגודל (סיום כתיבה) ──
        last = _size()
        if last <= 0:
            return
        stable = 0
        for _ in range(12):
            _t.sleep(0.25)
            cur = _size()
            if cur == last and cur > 0:
                stable += 1
                if stable >= 2:      # יציב פעמיים ברצף → הכתיבה הסתיימה
                    break
            else:
                last = cur; stable = 0
        if _size() <= 0:
            return

        # ── rename אטומי לשם ייחודי (מונע דריסה ע"י הדפסה הבאה) ──
        ts = _t.strftime("%Y%m%d_%H%M%S")
        dst = d / f"job_{ts}_{uuid.uuid4().hex[:6]}.pdf"
        try:
            os.replace(str(src), str(dst))
        except Exception:
            dst = src   # rename נכשל (קובץ נעול) — נשתמש במקור
        self.showNormal(); self.raise_(); self.activateWindow()
        self.load_file(str(dst))

    def _sel_option(self,idx):
        self.sel_opt=idx
        vis=[o for o in self.settings.get_options() if o.get("visible",True)]
        all_o=self.settings.get_options()
        for i,card in enumerate(self._opt_cards):
            ri=next((j for j,o in enumerate(all_o) if o.get("id")==vis[i].get("id")),0) if i<len(vis) else -1
            card.set_selected(ri==idx)
        self._rebuild_toggles()

    def _chg_copies(self,d):
        self.copies=max(1,min(99,self.copies+d)); self._copies_disp.setText(str(self.copies))

    def _choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,self.T("בחר קובץ","Choose File"),"",
            self.T("קבצים","Files")+" (*.pdf *.docx *.doc *.txt *.jpg *.jpeg *.png *.bmp *.tiff)")
        if path: self.load_file(path)

    def load_file(self,path):
        self.cur_file=path; p=Path(path); ext=p.suffix.lower()
        icons={".pdf":"📕",".docx":"📘",".doc":"📘",".txt":"📝",".jpg":"🖼️",".jpeg":"🖼️",".png":"🖼️"}
        self._file_ico.setText(icons.get(ext,"📄"))
        size=p.stat().st_size; sz=f"{size/1048576:.1f} MB" if size>100000 else f"{size//1024} KB"
        self._file_name.setText(p.name); self._file_meta.setText(f"{ext.upper().lstrip('.')} · {sz}")
        self._pages_badge.setText(self.T("נטען...","Loading...")); self._pages_badge.show()
        pages=self.print_engine.count_pages(path)
        if pages>0: self._pages_badge.setText(f"{pages} "+self.T("עמודים","pages"))
        else: self._pages_badge.hide()

    def _do_print(self):
        if not self.cur_file:
            QMessageBox.warning(self,self.T("שגיאה","Error"),self.T("יש לבחור קובץ","Please select a file")); return
        opts=self.settings.get_options()
        if self.sel_opt>=len(opts): return
        opt=opts[self.sel_opt]
        printer=opt.get("printer_override","") or getattr(self,"_sel_printer","")
        if not printer:
            QMessageBox.warning(self,self.T("שגיאה","Error"),self.T("לא נבחרה מדפסת","No printer selected")); return
        toggles={k:v for k,v in self.tog_states.items() if v}
        self._btn_print.setEnabled(False); self._btn_print.setText(self.T("⏳  שולח...","⏳  Sending...")); QApplication.processEvents()
        try:
            ok=self.print_engine.print_file(self.cur_file,opt,printer,self.copies,toggles)
            if ok:
                QMessageBox.information(self,self.T("הצלחה","Success"),self.T("המסמך נשלח למדפסת!","Document sent to printer!"))
                self.cur_file=None; self._file_ico.setText("📄")
                self._file_name.setText(self.T("גרור קובץ לכאן","Drag file here"))
                self._file_meta.setText(self.T("אין קובץ נבחר","No file selected")); self._pages_badge.hide()
            else:
                QMessageBox.critical(self,self.T("שגיאה","Error"),
                    self.T("שגיאה בשליחה.\nודא שהמדפסת מחוברת ומופעלת.","Print failed.\nCheck printer is connected and on."))
        finally:
            self._btn_print.setEnabled(True); self._btn_print.setText("🖨️  "+self.T("הדפס עכשיו","Print Now"))

    def _do_preview(self):
        if not self.cur_file:
            QMessageBox.information(self,self.T("תצוגה מקדימה","Preview"),self.T("יש לבחור קובץ","Please select a file")); return
        opts=self.settings.get_options()
        opt=opts[self.sel_opt] if self.sel_opt<len(opts) else {}
        try:
            from preview_dialog import PreviewDialog
            dlg=PreviewDialog(self,self.cur_file,self.lang,opt)
            dlg.exec()
        except ImportError:
            os.startfile(self.cur_file)

    def _open_settings(self, open_tab=None):
        if self.settings.get("password_enabled",True):
            dlg=PasswordDialog(self,self.lang)
            if dlg.exec()!=QDialog.DialogCode.Accepted: return
            if dlg.get_password()!=self.settings.get("password","1234"):
                QMessageBox.warning(self,self.T("שגיאה","Error"),self.T("סיסמה שגויה","Wrong password")); return
        try:
            dlg=SettingsPanel(self,self.settings,self.lang,self.dark_mode,open_tab=open_tab)
            if dlg.exec()==QDialog.DialogCode.Accepted:
                self.settings.save(); self.lang=self.settings.get("language","he")
                self.dark_mode=self.settings.get("dark_mode",False)
                self._apply_theme(); self._full_rebuild()
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))

    def _set_lang(self,lang):
        if self.lang==lang: return
        self.lang=lang; self.settings.set("language",lang); self.settings.save()
        self._refresh_lang_btns(); self._full_rebuild()

    def _toggle_dark(self):
        self.dark_mode=not self.dark_mode; self.settings.set("dark_mode",self.dark_mode); self.settings.save()
        self._dark_btn.setText("☀️" if self.dark_mode else "🌙"); self._apply_theme()
        self._rebuild_options_inner(); self._rebuild_toggles()

    def _full_rebuild(self):
        self._setup_window(); self._rebuild_options_inner(); self._rebuild_toggles()
        self._reload_printers(); self._apply_printer_visibility(); self._apply_cfg_btn_visibility()
        self._update_shortcut(); self._update_dir()
        self._dt.set_lang(self.lang)
        self._title_lbl.setText(APP_NAME if self.lang=="he" else APP_NAME_EN)
        self._ver_lbl.setText(f"v{VERSION}"); self._refresh_lang_btns(); self._update_all_text()

    def _update_all_text(self):
        self._printer_lbl.setText(self.T("מדפסת","Printer")); self._copies_lbl.setText(self.T("עותקים","Copies"))
        self._btn_print.setText("🖨️  "+self.T("הדפס עכשיו","Print Now")); self._btn_prev.setText(self.T("תצוגה מקדימה","Preview"))
        self._choose_btn.setText(self.T("📂  בחר קובץ","📂  Choose File"))
        if not self.cur_file:
            self._file_name.setText(self.T("גרור קובץ לכאן או לחץ לבחירה","Drag file here or click to choose"))
            self._file_meta.setText(self.T("אין קובץ נבחר","No file selected"))

    def _update_dir(self):
        d=Qt.LayoutDirection.RightToLeft if self.lang=="he" else Qt.LayoutDirection.LeftToRight
        self.setLayoutDirection(d)
        for w in self.findChildren(QWidget): w.setLayoutDirection(d)

    def T(self,he,en): return he if self.lang=="he" else en
    def _lbl(self,text,obj=""):
        l=QLabel(text); (l.setObjectName(obj) if obj else None); return l

    def _start_clock(self):
        self._timer=QTimer(); self._timer.timeout.connect(self._dt.update_time); self._timer.start(1000)

    def dragEnterEvent(self,e:QDragEnterEvent):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self,e:QDropEvent):
        urls=e.mimeData().urls()
        if urls: self.load_file(urls[0].toLocalFile())


# ════════════════════════════════════════════
LIGHT_SS = """
QMainWindow,QWidget         { background:#f0ece4; font-family:'Segoe UI','Arial',sans-serif; color:#1a1814; }
QWidget#body                { background:#f0ece4; }
QWidget#titleBar            { background:#ffffff; border-bottom:1px solid rgba(0,0,0,0.09); }
QLabel#appTitle             { font-size:15px; font-weight:700; color:#1a1814; background:transparent; }
QLabel#verLabel             { font-size:10px; color:#9a9690; background:transparent; }
QLabel#plainLbl             { background:transparent; border:none; }
QLabel                      { background:transparent; }
QFrame#fileBar              { background:#ffffff; border:1.5px solid rgba(0,0,0,0.10); border-radius:12px; }
QFrame#fileBar:hover        { border-color:rgba(74,124,89,0.5); }
QLabel#fileName             { font-size:14px; font-weight:600; color:#1a1814; }
QLabel#fileMeta             { font-size:12px; color:#8a8480; }
QLabel#pagesBadge           { background:#e8f3ec; color:#4a7c59; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:600; }
QLabel#sectionLabel         { font-size:11px; font-weight:700; color:#8a8480; }
QLabel#ctrlLbl              { font-size:11px; color:#8a8480; }
QWidget#togItem             { background:transparent; border:none; }
QLabel#togLabel             { font-size:13px; color:#1a1814; }
QPushButton#navArrow        { background:transparent; border:none; color:#4a7c59; font-size:20px; font-weight:700; border-radius:6px; }
QPushButton#navArrow:hover  { background:rgba(74,124,89,0.10); }
QComboBox#printerCombo      { background:#ffffff; border:1px solid rgba(0,0,0,0.12); border-radius:8px; padding:7px 12px; font-size:13px; color:#1a1814; min-height:34px; }
QComboBox#printerCombo::drop-down { border:none; width:22px; }
QComboBox#printerCombo QAbstractItemView { background:#ffffff; selection-background-color:#e8f3ec; color:#1a1814; }
QLabel#copiesCount          { font-size:15px; font-weight:700; color:#1a1814; }
QPushButton#copiesBtn       { background:#f5f1eb; border:1px solid rgba(0,0,0,0.10); border-radius:6px; font-size:16px; color:#1a1814; }
QPushButton#copiesBtn:hover { background:#e8f3ec; }
QPushButton#btnPrimary      { background:#4a7c59; color:white; border:none; border-radius:10px; font-size:15px; font-weight:700; padding:0 24px; }
QPushButton#btnPrimary:hover{ background:#3d6b4a; }
QPushButton#btnPrimary:disabled { background:#a0bfaa; }
QPushButton#btnSecondary    { background:#f5f1eb; color:#1a1814; border:1px solid rgba(0,0,0,0.12); border-radius:10px; font-size:13px; padding:0 18px; }
QPushButton#btnSecondary:hover { background:#ffffff; }
QFrame#langFrame            { background:#edeae4; border:1px solid rgba(0,0,0,0.14); border-radius:8px; }
QPushButton#langSegActive   { background:#4a7c59; color:white; border:none; border-radius:6px; font-size:12px; font-weight:700; }
QPushButton#langSegInactive { background:transparent; color:#6a6760; border:none; border-radius:6px; font-size:12px; }
QPushButton#langSegInactive:hover { color:#4a7c59; }
QPushButton#iconBtn         { background:#f5f1eb; border:1px solid rgba(0,0,0,0.12); border-radius:8px; font-size:15px; color:#1a1814; }
QPushButton#iconBtn:hover   { background:#ffffff; }
QScrollBar:vertical         { width:5px; background:transparent; border:none; }
QScrollBar::handle:vertical { background:rgba(0,0,0,0.15); border-radius:3px; }
QScrollBar::add-line,QScrollBar::sub-line { width:0; height:0; }
QDialog                     { background:#f8f6f2; color:#1a1814; }
QTabWidget::pane            { background:#f8f6f2; border:1px solid rgba(0,0,0,0.08); }
QTabBar::tab                { background:#ede9e3; padding:7px 13px; margin-right:2px; border-radius:6px 6px 0 0; color:#5a5650; font-size:12px; }
QTabBar::tab:selected       { background:#f8f6f2; font-weight:600; color:#4a7c59; }
QListWidget                 { background:#ffffff; border:1px solid rgba(0,0,0,0.10); border-radius:8px; color:#1a1814; }
QListWidget::item:selected  { background:#e8f3ec; color:#1a1814; }
QLineEdit                   { background:#ffffff; border:1px solid rgba(0,0,0,0.12); border-radius:7px; padding:7px 10px; font-size:13px; color:#1a1814; }
QLineEdit:focus             { border-color:#4a7c59; }
QComboBox                   { background:#ffffff; border:1px solid rgba(0,0,0,0.12); border-radius:7px; padding:6px 10px; font-size:13px; color:#1a1814; }
QComboBox::drop-down        { border:none; }
QComboBox QAbstractItemView { background:#ffffff; selection-background-color:#e8f3ec; color:#1a1814; }
QTextEdit                   { background:#1a1916; color:#a0e080; border-radius:6px; font-family:Consolas,monospace; font-size:11px; }
"""

DARK_SS = """
QMainWindow,QWidget         { background:#1a1916; font-family:'Segoe UI','Arial',sans-serif; color:#f0ece4; }
QWidget#body                { background:#1a1916; }
QWidget#titleBar            { background:#23211e; border-bottom:1px solid rgba(255,255,255,0.07); }
QLabel#appTitle             { font-size:15px; font-weight:700; color:#f0ece4; background:transparent; }
QLabel#verLabel             { font-size:10px; color:#605d58; background:transparent; }
QLabel#plainLbl             { background:transparent; border:none; }
QLabel                      { background:transparent; }
QFrame#fileBar              { background:#2c2a27; border:1.5px solid rgba(255,255,255,0.08); border-radius:12px; }
QFrame#fileBar:hover        { border-color:rgba(106,171,126,0.4); }
QLabel#fileName             { font-size:14px; font-weight:600; color:#f0ece4; }
QLabel#fileMeta             { font-size:12px; color:#706d68; }
QLabel#pagesBadge           { background:#1a2e20; color:#6aab7e; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:600; }
QLabel#sectionLabel         { font-size:11px; font-weight:700; color:#706d68; }
QLabel#ctrlLbl              { font-size:11px; color:#706d68; }
QWidget#togItem             { background:transparent; border:none; }
QLabel#togLabel             { font-size:13px; color:#f0ece4; }
QPushButton#navArrow        { background:transparent; border:none; color:#6aab7e; font-size:20px; font-weight:700; border-radius:6px; }
QPushButton#navArrow:hover  { background:rgba(106,171,126,0.12); }
QComboBox#printerCombo      { background:#2c2a27; border:1px solid rgba(255,255,255,0.10); border-radius:8px; padding:7px 12px; font-size:13px; color:#f0ece4; min-height:34px; }
QComboBox#printerCombo::drop-down { border:none; }
QComboBox#printerCombo QAbstractItemView { background:#2c2a27; selection-background-color:#1a2e20; color:#f0ece4; }
QLabel#copiesCount          { font-size:15px; font-weight:700; color:#f0ece4; }
QPushButton#copiesBtn       { background:#2c2a27; border:1px solid rgba(255,255,255,0.10); border-radius:6px; font-size:16px; color:#f0ece4; }
QPushButton#copiesBtn:hover { background:#1a2e20; }
QPushButton#btnPrimary      { background:#4a7c59; color:white; border:none; border-radius:10px; font-size:15px; font-weight:700; padding:0 24px; }
QPushButton#btnPrimary:hover{ background:#6aab7e; }
QPushButton#btnPrimary:disabled { background:#2a4a34; color:#5a8a6a; }
QPushButton#btnSecondary    { background:#2c2a27; color:#f0ece4; border:1px solid rgba(255,255,255,0.10); border-radius:10px; font-size:13px; padding:0 18px; }
QPushButton#btnSecondary:hover { background:#3a3835; }
QFrame#langFrame            { background:#2c2a27; border:1px solid rgba(255,255,255,0.12); border-radius:8px; }
QPushButton#langSegActive   { background:#4a7c59; color:white; border:none; border-radius:6px; font-size:12px; font-weight:700; }
QPushButton#langSegInactive { background:transparent; color:#908d88; border:none; border-radius:6px; font-size:12px; }
QPushButton#langSegInactive:hover { color:#6aab7e; }
QPushButton#iconBtn         { background:#2c2a27; border:1px solid rgba(255,255,255,0.10); border-radius:8px; font-size:15px; color:#f0ece4; }
QPushButton#iconBtn:hover   { background:#3a3835; }
QScrollBar:vertical         { width:5px; background:transparent; border:none; }
QScrollBar::handle:vertical { background:rgba(255,255,255,0.15); border-radius:3px; }
QScrollBar::add-line,QScrollBar::sub-line { width:0; height:0; }
QDialog                     { background:#23211e; color:#f0ece4; }
QTabWidget::pane            { background:#23211e; border:1px solid rgba(255,255,255,0.08); }
QTabBar::tab                { background:#2c2a27; padding:7px 13px; margin-right:2px; border-radius:6px 6px 0 0; color:#a0a09a; font-size:12px; }
QTabBar::tab:selected       { background:#23211e; font-weight:600; color:#6aab7e; }
QListWidget                 { background:#2c2a27; border:1px solid rgba(255,255,255,0.10); border-radius:8px; color:#f0ece4; }
QListWidget::item:selected  { background:#1a2e20; color:#f0ece4; }
QLineEdit                   { background:#2c2a27; border:1px solid rgba(255,255,255,0.12); border-radius:7px; padding:7px 10px; font-size:13px; color:#f0ece4; }
QLineEdit:focus             { border-color:#6aab7e; }
QComboBox                   { background:#2c2a27; border:1px solid rgba(255,255,255,0.12); border-radius:7px; padding:6px 10px; font-size:13px; color:#f0ece4; }
QComboBox::drop-down        { border:none; }
QComboBox QAbstractItemView { background:#2c2a27; selection-background-color:#1a2e20; color:#f0ece4; }
QTextEdit                   { background:#1a1916; color:#a0e080; border-radius:6px; font-family:Consolas,monospace; font-size:11px; }
"""


def main():
    if sys.platform=="win32": os.environ.setdefault("PYTHONIOENCODING","utf-8")

    # Handle --install-action when launched as admin from installer
    if "--install-action" in sys.argv:
        idx = sys.argv.index("--install-action")
        action = sys.argv[idx+1] if idx+1 < len(sys.argv) else "install"
        from install_printer import install, uninstall, is_admin
        if is_admin():
            if action=="uninstall": uninstall()
            else: install()
        sys.exit(0)

    app=QApplication(sys.argv); app.setApplicationName("HaMeviBLaDfus"); app.setOrganizationName("HaMeviBLaDfus")
    file_to_print=sys.argv[1] if len(sys.argv)>1 and not sys.argv[1].startswith("-") else None
    win=VirtualPrinterApp(file_to_print); win.show()
    sys.exit(app.exec())


if __name__=="__main__":
    main()
