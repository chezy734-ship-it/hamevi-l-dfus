#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI Components - Virtual Printer v1.2"""

import os, sys, subprocess, threading, tempfile
from datetime import datetime, date
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QDialog, QLineEdit, QTabWidget, QListWidget,
    QListWidgetItem, QComboBox, QCheckBox, QMessageBox,
    QFileDialog, QScrollArea, QSizePolicy, QTextEdit,
    QGroupBox, QButtonGroup, QRadioButton
)
from PyQt6.QtCore  import Qt, QTimer, pyqtSignal, QRect, QThread, pyqtSlot
from PyQt6.QtGui   import QPainter, QColor, QPen, QBrush, QFont, QPixmap

from hebrew_date import get_hebrew_date, get_gregorian_date_he

VERSION  = "1.2"
CREATE_NO_WINDOW = 0x08000000

APP_DESC_HE = "המביא לדפוס הוא כלי הדפסה וירטואלי חכם עבור Windows.\nשלח מסמכים מכל תוכנה למדפסת הווירטואלית ובחר אפשרות הדפסה מהירה."
APP_DESC_EN = "The Print Bringer is a smart virtual printer for Windows.\nSend documents from any app to the virtual printer and choose a quick print option."

# Popular shortcut suggestions
SHORTCUT_PRESETS = ["F8","F9","F10","Ctrl+P","Ctrl+Shift+P","Alt+P","Ctrl+Alt+P"]


# ══════════════════════════════════════════════════════════════════════════
#  Fix: StyledCheckBox — RTL draws indicator on RIGHT, LTR on LEFT
# ══════════════════════════════════════════════════════════════════════════

class StyledCheckBox(QWidget):
    stateChanged = pyqtSignal(int)

    def __init__(self, text="", checked=False, rtl=False, parent=None):
        super().__init__(parent)
        self._checked=checked; self._text=text; self._rtl=rtl
        self.setFixedHeight(28); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._font=QFont("Segoe UI",13); self.setMinimumWidth(200)

    def isChecked(self):   return self._checked
    def text(self):        return self._text
    def setText(self,t):   self._text=t; self.update()
    def setChecked(self,v): self._checked=bool(v); self.update(); self.stateChanged.emit(2 if v else 0)
    def mousePressEvent(self,e):
        self._checked=not self._checked; self.update(); self.stateChanged.emit(2 if self._checked else 0)

    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W=self.width(); H=self.height(); BS=18; BY=(H-BS)//2
        if self._rtl:
            bx=W-BS-4; text_rect=QRect(0,0,bx-6,H)
            ta=Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignRight
        else:
            bx=2; text_rect=QRect(bx+BS+8,0,W-BS-12,H)
            ta=Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft
        border=QColor("#4a7c59") if self._checked else QColor("#aaaaaa")
        p.setPen(QPen(border,1.5)); p.setBrush(QBrush(QColor("#ffffff") if self._checked else Qt.GlobalColor.transparent))
        p.drawRoundedRect(bx,BY,BS,BS,4,4)
        if self._checked:
            p.setPen(QPen(QColor("#4a7c59"),2.2,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
            cx=bx+BS//2; cy=BY+BS//2
            p.drawLine(bx+4,cy,cx-2,BY+BS-4); p.drawLine(cx-2,BY+BS-4,bx+BS-3,BY+4)
        p.setPen(QPen(QColor("#1a1814"))); p.setFont(self._font)
        p.drawText(text_rect,ta,self._text); p.end()


class DateTimeWidget(QWidget):
    def __init__(self,lang,settings,parent=None):
        super().__init__(parent); self.lang=lang; self.settings=settings; self.setFixedWidth(240)
        vl=QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(1); vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time=QLabel(); self._time.setAlignment(Qt.AlignmentFlag.AlignCenter); self._time.setFont(QFont("Segoe UI",17,QFont.Weight.Bold))
        self._heb=QLabel();  self._heb.setAlignment(Qt.AlignmentFlag.AlignCenter);  self._heb.setFont(QFont("Segoe UI",11))
        self._greg=QLabel(); self._greg.setAlignment(Qt.AlignmentFlag.AlignCenter); self._greg.setFont(QFont("Segoe UI",10))
        vl.addWidget(self._time); vl.addWidget(self._heb); vl.addWidget(self._greg); self.update_time()
    def set_lang(self,lang): self.lang=lang; self.update_time()
    def update_time(self):
        now=datetime.now(); today=date.today()
        show_time=self.settings.get("show_time",True); fmt24=self.settings.get("time_24h",True)
        if show_time: self._time.setText(now.strftime("%H:%M:%S") if fmt24 else now.strftime("%I:%M:%S %p")); self._time.show()
        else: self._time.hide()
        show_date=self.settings.get("show_date",True); mode=self.settings.get("date_mode","hebrew")
        if not show_date: self._heb.hide(); self._greg.hide(); return
        if mode in ("hebrew","both"): self._heb.setText(get_hebrew_date(today)); self._heb.show()
        elif mode=="gregorian": self._heb.setText(get_gregorian_date_he(today) if self.lang=="he" else today.strftime("%B %d, %Y")); self._heb.show()
        else: self._heb.hide()
        if mode=="both": self._greg.setText(get_gregorian_date_he(today) if self.lang=="he" else today.strftime("%B %d, %Y")); self._greg.show()
        else: self._greg.hide()


class ToggleSwitch(QWidget):
    toggled=pyqtSignal(bool)
    def __init__(self,parent=None): super().__init__(parent); self._c=False; self.setFixedSize(44,24); self.setCursor(Qt.CursorShape.PointingHandCursor)
    def isChecked(self): return self._c
    def setChecked(self,v): self._c=v; self.update()
    def mousePressEvent(self,e): self._c=not self._c; self.update(); self.toggled.emit(self._c)
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor("#4a7c59") if self._c else QColor("#cccccc"))); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(0,0,44,24,12,12)
        p.setBrush(QBrush(QColor("#ffffff"))); p.drawEllipse(22 if self._c else 2,2,20,20); p.end()


class OptionCard(QFrame):
    clicked_signal=pyqtSignal()
    def __init__(self,option,selected,lang,dark_mode,parent=None):
        super().__init__(parent); self.opt=option; self.lang=lang; self.dark_mode=dark_mode; self._sel=selected
        self.setFixedSize(150,168); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setObjectName("optionCard"); self._apply_style()
        vl=QVBoxLayout(self); vl.setContentsMargins(10,12,10,10); vl.setSpacing(6); vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(self._preview(),0,Qt.AlignmentFlag.AlignCenter)
        self._name=QLabel(option.get("name_he" if lang=="he" else "name_en",""))
        self._name.setAlignment(Qt.AlignmentFlag.AlignCenter); self._name.setWordWrap(True)
        self._name.setFont(QFont("Segoe UI",11,QFont.Weight.Bold)); self._name.setStyleSheet("color:#4a7c59;" if selected else "color:#1a1814;"); vl.addWidget(self._name)
        desc=QLabel(option.get("desc_he" if lang=="he" else "desc_en",""))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter); desc.setFont(QFont("Segoe UI",9)); desc.setStyleSheet("color:#8a8480;"); vl.addWidget(desc)
        self._chk=QLabel("✓"); self._chk.setParent(self)
        self._chk.setStyleSheet("background:#4a7c59;color:white;border-radius:10px;font-size:12px;font-weight:bold;padding:0 5px;")
        self._chk.setFixedSize(20,20); self._chk.setAlignment(Qt.AlignmentFlag.AlignCenter); self._chk.move(self.width()-26,6); self._chk.setVisible(selected)
    def _preview(self):
        lbl=QLabel(); lbl.setFixedSize(100,80); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img=self.opt.get("image_path","")
        if img and Path(img).exists():
            pix=QPixmap(img).scaled(100,80,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation); lbl.setPixmap(pix); return lbl
        pix=QPixmap(100,80); pix.fill(Qt.GlobalColor.transparent); self._draw(pix); lbl.setPixmap(pix); return lbl
    def _draw(self,pix):
        oid=self.opt.get("id","normal"); p=QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg=QColor("#e8f3ec"); bd=QColor("#4a7c59"); lc=QColor(74,124,89,100)
        def page(x,y,w,h):
            p.setBrush(QBrush(bg)); p.setPen(QPen(bd,1.5)); p.drawRoundedRect(x,y,w,h,3,3)
            p.setPen(QPen(lc,1.2)); [p.drawLine(x+6,y+10+i*8,x+w-6,y+10+i*8) for i in range(3)]
        if oid=="normal": page(20,5,60,70)
        elif oid in ("booklet_he","booklet_en"):
            page(5,5,42,70); page(53,5,42,70); p.setPen(QPen(bd,2)); p.drawLine(50,5,50,75)
            p.setFont(QFont("Arial",8,QFont.Weight.Bold)); p.setPen(QPen(bd))
            if oid=="booklet_he": p.drawText(QRect(5,58,42,14),Qt.AlignmentFlag.AlignCenter,"א"); p.drawText(QRect(53,58,42,14),Qt.AlignmentFlag.AlignCenter,"ב")
            else: p.drawText(QRect(5,58,42,14),Qt.AlignmentFlag.AlignCenter,"A"); p.drawText(QRect(53,58,42,14),Qt.AlignmentFlag.AlignCenter,"B")
        elif oid=="duplex": page(20,2,60,33); page(20,40,60,33)
        elif oid=="two_up": page(4,8,42,58); page(54,8,42,58)
        elif oid=="landscape": p.setBrush(QBrush(bg)); p.setPen(QPen(bd,1.5)); p.drawRoundedRect(5,20,90,40,3,3); p.setPen(QPen(lc,1.2)); [p.drawLine(14,28+i*8,86,28+i*8) for i in range(3)]
        elif oid=="four_up": page(4,4,42,34); page(54,4,42,34); page(4,42,42,34); page(54,42,42,34)
        else: p.setFont(QFont("Segoe UI Emoji",26)); p.setPen(QPen(bd)); p.drawText(QRect(0,0,100,80),Qt.AlignmentFlag.AlignCenter,self.opt.get("icon","📄"))
        p.end()
    def set_selected(self,v): self._sel=v; self._apply_style(); self._chk.setVisible(v); self._name.setStyleSheet("color:#4a7c59;" if v else "color:#1a1814;")
    def _apply_style(self):
        if self._sel: self.setStyleSheet("QFrame#optionCard{background:#e8f3ec;border:2px solid #4a7c59;border-radius:12px;}")
        else:
            bg="#2c2a27" if self.dark_mode else "#ffffff"
            self.setStyleSheet(f"QFrame#optionCard{{background:{bg};border:2px solid rgba(0,0,0,0.09);border-radius:12px;}}QFrame#optionCard:hover{{border-color:#4a7c59;}}")
    def mousePressEvent(self,e): self.clicked_signal.emit()


class PasswordDialog(QDialog):
    def __init__(self,parent,lang,prompt=""):
        super().__init__(parent); self.lang=lang; T=lambda h,e:h if lang=="he" else e
        self.setWindowTitle(T("הגנת הגדרות","Protected Settings")); self.setFixedSize(300,185)
        vl=QVBoxLayout(self); vl.setContentsMargins(24,18,24,18); vl.setSpacing(10)
        ico=QLabel("🔒"); ico.setFont(QFont("Segoe UI Emoji",32)); ico.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(ico)
        msg=QLabel(prompt or T("הזן סיסמה","Enter password")); msg.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(msg)
        self._inp=QLineEdit(); self._inp.setEchoMode(QLineEdit.EchoMode.Password)
        self._inp.setPlaceholderText(T("סיסמה","Password")); self._inp.setFixedHeight(36); self._inp.returnPressed.connect(self.accept); vl.addWidget(self._inp)
        br=QHBoxLayout()
        ok=QPushButton(T("כניסה","Enter")); ok.setObjectName("btnPrimary"); ok.setFixedHeight(34); ok.clicked.connect(self.accept)
        cn=QPushButton(T("ביטול","Cancel")); cn.setObjectName("btnSecondary"); cn.setFixedHeight(34); cn.clicked.connect(self.reject)
        br.addWidget(ok); br.addWidget(cn); vl.addLayout(br)
    def get_password(self): return self._inp.text()


# ══════════════════════════════════════════════════════════════════════════
#  Settings Panel
# ══════════════════════════════════════════════════════════════════════════

class SettingsPanel(QDialog):
    def __init__(self,parent,settings,lang,dark_mode,open_tab=None):
        super().__init__(parent); self.settings=settings; self.lang=lang; self.dark_mode=dark_mode
        self.setWindowTitle(self.T("הגדרות","Settings")); self.setMinimumSize(700,640); self.resize(740,680)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang=="he" else Qt.LayoutDirection.LeftToRight)
        vl=QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)
        hdr=QFrame(); hdr.setFixedHeight(54); hdr.setStyleSheet("background:#4a7c59;border:none;")
        hl=QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0)
        ht=QLabel("⚙️  "+self.T("הגדרות המביא לדפוס","Virtual Printer Settings"))
        ht.setFont(QFont("Segoe UI",13,QFont.Weight.Bold)); ht.setStyleSheet("color:white;background:transparent;"); hl.addWidget(ht)
        vl.addWidget(hdr)
        self.tabs=QTabWidget(); self.tabs.setDocumentMode(True); vl.addWidget(self.tabs,1)
        self._tab_options(); self._tab_printers(); self._tab_install()
        self._tab_security(); self._tab_general(); self._tab_about()
        ftr=QFrame(); ftr.setFixedHeight(64); ftr.setStyleSheet("border-top:1px solid rgba(0,0,0,0.10);")
        fl=QHBoxLayout(ftr); fl.setContentsMargins(20,0,20,0); fl.setSpacing(10); fl.addStretch()
        save=QPushButton("✅  "+self.T("שמור שינויים","Save Changes"))
        save.setFixedHeight(44); save.setMinimumWidth(160); save.setFont(QFont("Segoe UI",13,QFont.Weight.Bold))
        save.setStyleSheet("QPushButton{background:#4a7c59;color:white;border:none;border-radius:10px;font-size:14px;font-weight:700;padding:0 24px;}QPushButton:hover{background:#3d6b4a;}")
        save.clicked.connect(self._save)
        cn=QPushButton(self.T("ביטול","Cancel")); cn.setObjectName("btnSecondary"); cn.setFixedHeight(44); cn.setMinimumWidth(100); cn.clicked.connect(self.reject)
        fl.addWidget(save); fl.addWidget(cn); vl.addWidget(ftr)

        if open_tab:
            tab_names={"install":2,"security":3,"general":4}
            if open_tab in tab_names: self.tabs.setCurrentIndex(tab_names[open_tab])

    def T(self,he,en): return he if self.lang=="he" else en
    def rtl(self): return self.lang=="he"
    def _cb(self,text,checked): return StyledCheckBox(text,checked,rtl=self.rtl())
    def _sec(self,t): l=QLabel(t); l.setFont(QFont("Segoe UI",10,QFont.Weight.Bold)); l.setStyleSheet("color:#4a7c59;margin-top:6px;"); return l

    # ── Options tab ────────────────────────────────────────────────────────
    def _tab_options(self):
        tab=QWidget(); vl=QVBoxLayout(tab); vl.setContentsMargins(16,14,16,14); vl.setSpacing(8)
        vl.addWidget(self._sec(self.T("אפשרויות הדפסה מהירה","Quick Print Options")))
        note=QLabel(self.T("סמן ✓ להצגת אפשרות. לחץ פעמיים לעריכה.","Check ✓ to show. Double-click to edit."))
        note.setStyleSheet("color:#8a8480;font-size:12px;"); vl.addWidget(note)
        self._opts_list=QListWidget(); self._opts_list.setAlternatingRowColors(True); self._opts_list.itemDoubleClicked.connect(self._edit_opt)
        self._reload_opts(); vl.addWidget(self._opts_list)
        br=QHBoxLayout()
        for lbl,fn in [(self.T("➕ הוסף","➕ Add"),self._add_opt),(self.T("✏️ ערוך","✏️ Edit"),self._edit_opt),(self.T("🗑️ מחק","🗑️ Delete"),self._del_opt)]:
            b=QPushButton(lbl); b.setObjectName("btnSecondary"); b.clicked.connect(fn); br.addWidget(b)
        vl.addLayout(br); self.tabs.addTab(tab,self.T("אפשרויות","Options"))

    def _reload_opts(self):
        try: self._opts_list.itemChanged.disconnect()
        except: pass
        self._opts_list.clear()
        for opt in self.settings.get_options():
            name=opt.get("name_he" if self.lang=="he" else "name_en","")
            item=QListWidgetItem(f"  {opt.get('icon','📄')}  {name}")
            item.setData(Qt.ItemDataRole.UserRole,opt)
            item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if opt.get("visible",True) else Qt.CheckState.Unchecked)
            self._opts_list.addItem(item)
        self._opts_list.itemChanged.connect(self._on_opt_check)

    def _on_opt_check(self,item):
        opt=item.data(Qt.ItemDataRole.UserRole)
        if not opt: return
        opts=self.settings.get_options()
        for o in opts:
            if o.get("id")==opt.get("id"): o["visible"]=item.checkState()==Qt.CheckState.Checked; break
        self.settings.set_options(opts)

    def _add_opt(self,*_):
        dlg=OptionEditDialog(self,None,self.lang,self.settings.get_toggles(),self._printers())
        if dlg.exec()==QDialog.DialogCode.Accepted:
            opts=self.settings.get_options(); opts.append(dlg.get_option()); self.settings.set_options(opts); self._reload_opts()

    def _edit_opt(self,*_):
        item=self._opts_list.currentItem()
        if not item: return
        opt=item.data(Qt.ItemDataRole.UserRole)
        dlg=OptionEditDialog(self,opt,self.lang,self.settings.get_toggles(),self._printers())
        if dlg.exec()==QDialog.DialogCode.Accepted:
            updated=dlg.get_option(); opts=self.settings.get_options()
            for i,o in enumerate(opts):
                if o.get("id")==opt.get("id"): opts[i]=updated; break
            self.settings.set_options(opts); self._reload_opts()

    def _del_opt(self,*_):
        item=self._opts_list.currentItem()
        if not item: return
        opts=self.settings.get_options()
        if len(opts)<=1: QMessageBox.warning(self,"",self.T("חייבת להישאר לפחות אפשרות","At least one option required")); return
        opt=item.data(Qt.ItemDataRole.UserRole)
        self.settings.set_options([o for o in opts if o.get("id")!=opt.get("id")]); self._reload_opts()

    def _printers(self):
        from print_engine import PrintEngine; return PrintEngine.get_system_printers()

    # ── Printers tab ───────────────────────────────────────────────────────
    def _tab_printers(self):
        from print_engine import PrintEngine
        tab=QWidget(); vl=QVBoxLayout(tab); vl.setContentsMargins(16,14,16,14); vl.setSpacing(10)
        vl.addWidget(self._sec(self.T("הגדרות מדפסת","Printer Settings")))
        self._show_printer_cb=self._cb(self.T("הצג בחירת מדפסת בחלון הראשי","Show printer selector in main window"),self.settings.get("show_printer_selector",True))
        vl.addWidget(self._show_printer_cb)
        vl.addWidget(QLabel(self.T("מדפסת ברירת מחדל:","Default Printer:")))
        self._default_combo=QComboBox(); printers=PrintEngine.get_system_printers()
        for p in printers: self._default_combo.addItem(p)
        default=self.settings.get("default_printer","")
        if default in printers: self._default_combo.setCurrentText(default)
        vl.addWidget(self._default_combo); vl.addStretch()
        self.tabs.addTab(tab,self.T("מדפסות","Printers"))

    # ── Fix #1 & #5: Installation tab ─────────────────────────────────────
    def _tab_install(self):
        tab=QWidget(); vl=QVBoxLayout(tab); vl.setContentsMargins(16,14,16,14); vl.setSpacing(10)
        vl.addWidget(self._sec(self.T("התקנת מדפסת וירטואלית","Virtual Printer Installation")))

        # Status indicator
        sf=QFrame(); sf.setStyleSheet("border:1px solid rgba(0,0,0,0.10);border-radius:8px;background:transparent;")
        sfl=QHBoxLayout(sf); sfl.setContentsMargins(14,10,14,10)
        self._dot=QLabel("●"); self._dot.setFont(QFont("Segoe UI",14))
        self._status_lbl=QLabel(self.T("בודק סטטוס...","Checking...")); self._status_lbl.setFont(QFont("Segoe UI",12))
        sfl.addWidget(self._dot); sfl.addWidget(self._status_lbl); sfl.addStretch()
        vl.addWidget(sf)

        note=QLabel(self.T(
            "לחץ 'התקן מדפסת' — חלון אישור הרשאות (UAC) יופיע.\n"
            "לחץ 'כן' להמשך ההתקנה. ההתקנה יכולה לקחת כ-30 שניות.",
            "Click 'Install Printer' — a UAC permission window will appear.\n"
            "Click 'Yes' to continue. Installation may take ~30 seconds."
        ))
        note.setWordWrap(True); note.setStyleSheet("color:#8a8480;font-size:12px;"); vl.addWidget(note)

        self._install_log=QTextEdit(); self._install_log.setReadOnly(True); self._install_log.setFixedHeight(150)
        vl.addWidget(self._install_log)

        br=QHBoxLayout(); br.setSpacing(10)
        self._btn_inst=QPushButton("🖨️  "+self.T("התקן מדפסת","Install Printer")); self._btn_inst.setFixedHeight(40)
        self._btn_inst.setStyleSheet("QPushButton{background:#4a7c59;color:white;border:none;border-radius:8px;font-size:13px;font-weight:700;padding:0 20px;}QPushButton:hover{background:#3d6b4a;}")
        self._btn_inst.clicked.connect(self._do_install)
        self._btn_uninst=QPushButton("🗑️  "+self.T("הסר מדפסת","Uninstall")); self._btn_uninst.setObjectName("btnSecondary"); self._btn_uninst.setFixedHeight(40)
        self._btn_uninst.clicked.connect(self._do_uninstall)
        self._btn_ref=QPushButton(self.T("🔄 רענן","🔄 Refresh")); self._btn_ref.setObjectName("btnSecondary"); self._btn_ref.setFixedHeight(40)
        self._btn_ref.clicked.connect(self._check_status)
        br.addWidget(self._btn_inst); br.addWidget(self._btn_uninst); br.addWidget(self._btn_ref)
        vl.addLayout(br); vl.addStretch()
        self.tabs.addTab(tab,self.T("התקנה","Installation"))
        QTimer.singleShot(300,self._check_status)

    def _check_status(self):
        try:
            from install_printer import is_installed
            if is_installed():
                self._dot.setStyleSheet("color:#4a7c59;")
                self._status_lbl.setText(self.T("✅  המדפסת מותקנת ופעילה","✅  Printer installed and active"))
            else:
                self._dot.setStyleSheet("color:#c0392b;")
                self._status_lbl.setText(self.T("❌  המדפסת אינה מותקנת","❌  Printer is not installed"))
        except Exception as e:
            self._status_lbl.setText(f"? {e}")

    def _run_action(self, action):
        """Fix #1 & #5: Use ShellExecuteW to elevate — shows UAC dialog, runs silently."""
        import ctypes
        self._install_log.clear()
        self._btn_inst.setEnabled(False); self._btn_uninst.setEnabled(False)

        self._install_log.append(self.T("מבקש הרשאות מנהל מערכת (UAC)...","Requesting Administrator rights (UAC)..."))
        self._install_log.append(self.T("אשר את חלון ההרשאות שיופיע.","Approve the permission window that appears."))

        def run():
            try:
                from install_printer import is_admin, install, uninstall, get_port_path, run_ps

                if is_admin():
                    # Already admin — run directly
                    if action=="uninstall": ok,msg=uninstall()
                    else: ok,msg=install()
                    self._install_log.append(msg)
                    self._install_log.append(self.T("✅ הצלחה!" if ok else "❌ נכשל","✅ Success!" if ok else "❌ Failed"))
                else:
                    # Fix #1: Use ShellExecuteW with "runas" — this shows UAC
                    script=Path(sys.executable).parent/"install_printer.py"
                    if not script.exists():
                        # Try next to the current script/exe
                        script=Path(__file__).parent/"install_printer.py"
                    if not script.exists():
                        self._install_log.append(self.T("❌ install_printer.py לא נמצא","❌ install_printer.py not found")); return

                    ret=ctypes.windll.shell32.ShellExecuteW(
                        None,"runas",sys.executable,f'"{script}" {action}',None,1
                    )
                    if ret<=32:
                        self._install_log.append(self.T("❌ בוטל על ידי המשתמש","❌ Cancelled by user")); return

                    import time; time.sleep(5)
                    self._install_log.append(self.T("ממתין לסיום ההתקנה...","Waiting for installation to finish..."))
                    time.sleep(8)
                    self._check_status()
                    if hasattr(self,'_dot') and "✅" in self._dot.styleSheet():
                        self._install_log.append(self.T("✅ המדפסת הותקנה בהצלחה!","✅ Printer installed successfully!"))
                    else:
                        self._install_log.append(self.T("בדוק סטטוס — לחץ 'רענן'","Check status — click Refresh"))
            except Exception as e:
                self._install_log.append(f"Error: {e}")
            finally:
                self._btn_inst.setEnabled(True); self._btn_uninst.setEnabled(True)

        t=threading.Thread(target=run,daemon=True); t.start()

    def _do_install(self):   self._install_log.clear(); self._run_action("install")
    def _do_uninstall(self):
        if QMessageBox.question(self,"",self.T("להסיר את המדפסת?","Remove printer?"),
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes: return
        self._install_log.clear(); self._run_action("uninstall")

    # ── Fix #11: Security tab — includes settings button toggle & shortcut ─
    def _tab_security(self):
        tab=QWidget(); vl=QVBoxLayout(tab); vl.setContentsMargins(16,14,16,14); vl.setSpacing(10)
        vl.addWidget(self._sec(self.T("הגנת סיסמה","Password Protection")))
        self._pwd_cb=self._cb(self.T("הפעל הגנת סיסמה על ההגדרות","Enable password protection"),self.settings.get("password_enabled",True))
        self._pwd_cb_last=self._pwd_cb.isChecked(); self._pwd_cb.stateChanged.connect(self._on_pwd_cb)
        vl.addWidget(self._pwd_cb)
        vl.addWidget(self._sec(self.T("שינוי סיסמה","Change Password")))
        note=QLabel(self.T("לשינוי – הזן סיסמה נוכחית וסיסמה חדשה:","Enter current and new password to change:"))
        note.setStyleSheet("color:#8a8480;font-size:12px;"); vl.addWidget(note)
        self._cur_pwd=QLineEdit(); self._cur_pwd.setEchoMode(QLineEdit.EchoMode.Password); self._cur_pwd.setPlaceholderText(self.T("סיסמה נוכחית","Current password")); self._cur_pwd.setFixedHeight(34); vl.addWidget(self._cur_pwd)
        self._new_pwd=QLineEdit(); self._new_pwd.setEchoMode(QLineEdit.EchoMode.Password); self._new_pwd.setPlaceholderText(self.T("סיסמה חדשה","New password")); self._new_pwd.setFixedHeight(34); vl.addWidget(self._new_pwd)
        sb=QPushButton(self.T("💾 שמור סיסמה חדשה","💾 Save New Password")); sb.setObjectName("btnPrimary"); sb.setFixedHeight(36); sb.clicked.connect(self._change_pwd); vl.addWidget(sb)

        # Fix #11: Settings button visibility + shortcut moved here
        vl.addWidget(self._sec(self.T("כפתור הגדרות","Settings Button")))
        self._show_cfg_cb=self._cb(self.T("הצג כפתור ⚙️ הגדרות בחלון הראשי","Show ⚙️ settings button in main window"),self.settings.get("show_settings_btn",True))
        vl.addWidget(self._show_cfg_cb)

        vl.addWidget(self._sec(self.T("מקש קיצור לפתיחת הגדרות","Keyboard Shortcut for Settings")))
        # Preset buttons
        preset_row=QHBoxLayout(); preset_row.setSpacing(6)
        for key in SHORTCUT_PRESETS:
            b=QPushButton(key); b.setObjectName("btnSecondary"); b.setFixedHeight(28)
            b.setFixedWidth(80 if len(key)>3 else 46)
            b.clicked.connect(lambda _,k=key: self._sh_inp.setText(k))
            preset_row.addWidget(b)
        preset_row.addStretch(); vl.addLayout(preset_row)

        sh_row=QHBoxLayout()
        self._sh_inp=QLineEdit(self.settings.get("settings_shortcut","F8"))
        self._sh_inp.setFixedWidth(120); self._sh_inp.setFixedHeight(34)
        self._sh_inp.setPlaceholderText(self.T("מקש קיצור","Shortcut key"))
        sh_row.addWidget(QLabel(self.T("מותאם אישית:","Custom:"))); sh_row.addWidget(self._sh_inp); sh_row.addStretch()
        vl.addLayout(sh_row)
        ex=QLabel(self.T(
            "דוגמאות: F8 | F9 | Ctrl+P | Ctrl+Shift+P | Alt+S",
            "Examples: F8 | F9 | Ctrl+P | Ctrl+Shift+P | Alt+S"
        )); ex.setStyleSheet("color:#8a8480;font-size:11px;"); vl.addWidget(ex)
        vl.addStretch()
        self.tabs.addTab(tab,self.T("אבטחה","Security"))

    def _on_pwd_cb(self,state):
        if state==0 and self._pwd_cb_last:
            dlg=PasswordDialog(self,self.lang,self.T("הזן סיסמה כדי לבטל","Enter password to disable"))
            if dlg.exec()!=QDialog.DialogCode.Accepted or dlg.get_password()!=self.settings.get("password","1234"):
                QMessageBox.warning(self,"",self.T("סיסמה שגויה","Wrong password")); self._pwd_cb.setChecked(True); return
        self._pwd_cb_last=bool(state)

    def _change_pwd(self):
        cur=self._cur_pwd.text(); new=self._new_pwd.text().strip()
        if self.settings.get("password_enabled",True) and cur!=self.settings.get("password","1234"):
            QMessageBox.warning(self,"",self.T("סיסמה נוכחית שגויה","Wrong current password")); return
        if not new: QMessageBox.warning(self,"",self.T("נא להזין סיסמה חדשה","Enter new password")); return
        self.settings.set("password",new); self.settings.set("password_enabled",True); self._pwd_cb.setChecked(True)
        self._cur_pwd.clear(); self._new_pwd.clear(); QMessageBox.information(self,"",self.T("הסיסמה עודכנה!","Password updated!"))

    # ── General tab ────────────────────────────────────────────────────────
    def _tab_general(self):
        tab=QWidget(); vl=QVBoxLayout(tab); vl.setContentsMargins(16,14,16,14); vl.setSpacing(10)
        vl.addWidget(self._sec(self.T("הצגת תאריך","Date Display")))
        self._show_date_cb=self._cb(self.T("הצג תאריך","Show date"),self.settings.get("show_date",True))
        vl.addWidget(self._show_date_cb)
        vl.addWidget(QLabel(self.T("סוג תאריך:","Date type:")))
        self._date_mode=QComboBox()
        self._date_mode.addItem(self.T("עברי בלבד","Hebrew only"),"hebrew")
        self._date_mode.addItem(self.T("לועזי בלבד","Gregorian only"),"gregorian")
        self._date_mode.addItem(self.T("עברי ולועזי יחד","Both"),"both")
        cur=self.settings.get("date_mode","hebrew")
        for i in range(self._date_mode.count()):
            if self._date_mode.itemData(i)==cur: self._date_mode.setCurrentIndex(i); break
        vl.addWidget(self._date_mode)
        vl.addWidget(self._sec(self.T("הצגת שעה","Time Display")))
        self._show_time_cb=self._cb(self.T("הצג שעה","Show time"),self.settings.get("show_time",True))
        self._time24_cb=self._cb(self.T("פורמט 24 שעות","24-hour format"),self.settings.get("time_24h",True))
        vl.addWidget(self._show_time_cb); vl.addWidget(self._time24_cb)
        vl.addWidget(self._sec(self.T("הפעלה אוטומטית","Auto Start")))
        self._startup_cb=self._cb(self.T("הפעל בעת אתחול Windows (מומלץ!)","Start with Windows (Recommended!)"),self.settings.get("start_with_windows",False))
        note=QLabel(self.T("חייב להיות מופעל כדי שהדפסה מ-Word/Chrome תיפתח אוטומטית!","Required for printing from Word/Chrome to open automatically!"))
        note.setStyleSheet("color:#c07020;font-size:11px;font-weight:600;"); note.setWordWrap(True)
        vl.addWidget(self._startup_cb); vl.addWidget(note)
        br=QHBoxLayout()
        for lbl,fn in [(self.T("📤 ייצא","📤 Export"),self._export),(self.T("📥 ייבא","📥 Import"),self._import),(self.T("🔄 אפס","🔄 Reset"),self._reset_all)]:
            b=QPushButton(lbl); b.setObjectName("btnSecondary"); b.clicked.connect(fn); br.addWidget(b)
        vl.addLayout(br); vl.addStretch(); self.tabs.addTab(tab,self.T("כללי","General"))

    # ── About tab ──────────────────────────────────────────────────────────
    def _tab_about(self):
        tab=QWidget(); vl=QVBoxLayout(tab); vl.setContentsMargins(24,20,24,20); vl.setSpacing(14)
        ico=QLabel("🖨️"); ico.setFont(QFont("Segoe UI Emoji",48)); ico.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(ico)
        name=QLabel(self.T("המביא לדפוס","The Print Bringer"))
        name.setFont(QFont("Segoe UI",18,QFont.Weight.Bold)); name.setAlignment(Qt.AlignmentFlag.AlignCenter); name.setStyleSheet("color:#4a7c59;"); vl.addWidget(name)
        ver=QLabel(f"גרסה / Version  {VERSION}"); ver.setAlignment(Qt.AlignmentFlag.AlignCenter); ver.setStyleSheet("color:#8a8480;font-size:12px;"); vl.addWidget(ver)
        line=QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("border:1px solid rgba(0,0,0,0.08);"); vl.addWidget(line)
        desc=QLabel(self.T(APP_DESC_HE,APP_DESC_EN)); desc.setWordWrap(True); desc.setAlignment(Qt.AlignmentFlag.AlignCenter); desc.setFont(QFont("Segoe UI",12)); vl.addWidget(desc)
        vl.addStretch(); self.tabs.addTab(tab,self.T("אודות","About"))

    def _export(self):
        import json; p,_=QFileDialog.getSaveFileName(self,"","settings.json","JSON (*.json)")
        if p:
            with open(p,"w",encoding="utf-8") as f: json.dump(self.settings._config,f,ensure_ascii=False,indent=2)

    def _import(self):
        import json; p,_=QFileDialog.getOpenFileName(self,"","","JSON (*.json)")
        if p:
            try:
                with open(p,"r",encoding="utf-8") as f: loaded=json.load(f)
                self.settings._config.update(loaded); QMessageBox.information(self,"",self.T("ייבוא הצליח","Imported"))
            except Exception as e: QMessageBox.critical(self,"",str(e))

    def _reset_all(self):
        if QMessageBox.question(self,"",self.T("לאפס את כל ההגדרות?","Reset all settings?"),
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.settings.reset_to_defaults(); self.accept()

    def _save(self):
        try:
            self.settings.set("password_enabled",self._pwd_cb.isChecked())
            self.settings.set("show_printer_selector",self._show_printer_cb.isChecked())
            self.settings.set("default_printer",self._default_combo.currentText())
            self.settings.set("show_date",self._show_date_cb.isChecked())
            self.settings.set("date_mode",self._date_mode.currentData())
            self.settings.set("show_time",self._show_time_cb.isChecked())
            self.settings.set("time_24h",self._time24_cb.isChecked())
            self.settings.set("show_settings_btn",self._show_cfg_cb.isChecked())
            self.settings.set("settings_shortcut",self._sh_inp.text().strip() or "F8")
            self.settings.set("start_with_windows",self._startup_cb.isChecked())
            self._apply_startup()
            self.settings.save(); self.accept()
        except Exception as e: QMessageBox.critical(self,self.T("שגיאה","Error"),str(e))

    def _apply_startup(self):
        try:
            import winreg
            key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Run",0,winreg.KEY_SET_VALUE)
            if self._startup_cb.isChecked():
                winreg.SetValueEx(key,"HaMeviBLaDfus",0,winreg.REG_SZ,f'"{sys.executable}"')
            else:
                try: winreg.DeleteValue(key,"HaMeviBLaDfus")
                except FileNotFoundError: pass
            winreg.CloseKey(key)
        except Exception: pass


class OptionEditDialog(QDialog):
    def __init__(self,parent,option,lang,all_toggles,all_printers):
        super().__init__(parent); self.lang=lang; self.existing=option
        T=self.T; is_new=option is None
        self.setWindowTitle(T("הוסף אפשרות","Add Option") if is_new else T("ערוך אפשרות","Edit Option"))
        self.setMinimumSize(480,600)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang=="he" else Qt.LayoutDirection.LeftToRight)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content=QWidget(); cl=QVBoxLayout(content); cl.setContentsMargins(20,16,20,8); cl.setSpacing(8)
        def row(l,w): cl.addWidget(QLabel(l)); cl.addWidget(w)
        self._name_he=QLineEdit(option.get("name_he","") if option else ""); self._name_he.setFixedHeight(34); row(T("שם בעברית:","Hebrew name:"),self._name_he)
        self._name_en=QLineEdit(option.get("name_en","") if option else ""); self._name_en.setFixedHeight(34); row(T("שם באנגלית:","English name:"),self._name_en)
        self._desc_he=QLineEdit(option.get("desc_he","") if option else ""); self._desc_he.setFixedHeight(34); row(T("תיאור בעברית:","Hebrew desc:"),self._desc_he)
        self._desc_en=QLineEdit(option.get("desc_en","") if option else ""); self._desc_en.setFixedHeight(34); row(T("תיאור באנגלית:","English desc:"),self._desc_en)
        self._icon=QLineEdit(option.get("icon","📄") if option else "📄"); self._icon.setFixedHeight(34); row(T("אייקון:","Icon:"),self._icon)
        ir=QHBoxLayout(); self._img=QLineEdit(option.get("image_path","") if option else ""); self._img.setPlaceholderText(T("נתיב תמונה (רשות)","Image path (optional)")); self._img.setFixedHeight(34)
        br2=QPushButton("📂"); br2.setObjectName("btnSecondary"); br2.setFixedSize(34,34); br2.clicked.connect(self._browse); ir.addWidget(self._img); ir.addWidget(br2)
        cl.addWidget(QLabel(T("תמונה:","Image:"))); cl.addLayout(ir)

        # Toggles with description
        cl.addWidget(QLabel(T("מתגים לאפשרות זו:","Toggles for this option:")))
        tog_note=QLabel(T("מתגים הם הגדרות נוספות שיוצגו לבחירה בעת הדפסה","Toggles appear as extra settings when printing"))
        tog_note.setStyleSheet("color:#8a8480;font-size:11px;"); cl.addWidget(tog_note)
        self._tog_cbs={}
        existing_togs=option.get("toggles",[]) if option else []
        for tog in all_toggles:
            cb=StyledCheckBox(f"{tog.get('name_he','')} / {tog.get('name_en','')}", tog.get("id") in existing_togs, rtl=(lang=="he"))
            self._tog_cbs[tog.get("id")]=cb; cl.addWidget(cb)

        cl.addWidget(QLabel(T("מדפסת ייעודית לאפשרות זו:","Dedicated printer for this option:")))
        ded_note=QLabel(T("השאר 'ברירת מחדל' להשתמש במדפסת הנבחרת בחלון הראשי","Leave 'Default' to use the printer selected in main window"))
        ded_note.setStyleSheet("color:#8a8480;font-size:11px;"); cl.addWidget(ded_note)
        self._pc=QComboBox(); self._pc.addItem(T("ברירת מחדל","Default"),"")
        for p in all_printers: self._pc.addItem(p,p)
        override=option.get("printer_override","") if option else ""
        if override:
            for i in range(self._pc.count()):
                if self._pc.itemData(i)==override: self._pc.setCurrentIndex(i); break
        cl.addWidget(self._pc); cl.addStretch(); scroll.setWidget(content)
        main=QVBoxLayout(self); main.setContentsMargins(0,0,0,0); main.setSpacing(0); main.addWidget(scroll,1)
        ftr=QFrame(); ftr.setFixedHeight(54); ftr.setStyleSheet("border-top:1px solid rgba(0,0,0,0.08);")
        fl=QHBoxLayout(ftr); fl.setContentsMargins(16,0,16,0); fl.setSpacing(10); fl.addStretch()
        ok=QPushButton(T("💾 שמור","💾 Save"))
        ok.setStyleSheet("QPushButton{background:#4a7c59;color:white;border:none;border-radius:8px;font-size:13px;font-weight:700;padding:0 20px;}QPushButton:hover{background:#3d6b4a;}")
        ok.setFixedHeight(36); ok.clicked.connect(self.accept)
        cn=QPushButton(T("ביטול","Cancel")); cn.setObjectName("btnSecondary"); cn.setFixedHeight(36); cn.clicked.connect(self.reject)
        fl.addWidget(ok); fl.addWidget(cn); main.addWidget(ftr)

    def T(self,he,en): return he if self.lang=="he" else en
    def _browse(self):
        p,_=QFileDialog.getOpenFileName(self,"","","Images (*.png *.jpg *.jpeg *.bmp)")
        if p: self._img.setText(p)

    def get_option(self):
        import uuid
        eid=self.existing.get("id",f"opt_{uuid.uuid4().hex[:8]}") if self.existing else f"opt_{uuid.uuid4().hex[:8]}"
        return {
            "id":eid,"name_he":self._name_he.text().strip() or "אפשרות","name_en":self._name_en.text().strip() or "Option",
            "desc_he":self._desc_he.text().strip(),"desc_en":self._desc_en.text().strip(),"icon":self._icon.text().strip() or "📄",
            "image_path":self._img.text().strip(),"toggles":[tid for tid,cb in self._tog_cbs.items() if cb.isChecked()],
            "printer_override":self._pc.currentData() or "","visible":self.existing.get("visible",True) if self.existing else True,
        }
