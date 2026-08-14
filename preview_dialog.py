#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preview_dialog.py - Document preview inside the tool.
Requires: pip install PyMuPDF
Auto-fits to window on open. Shows layout based on selected print option.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QSizePolicy
)
from PyQt6.QtCore  import Qt, QSize
from PyQt6.QtGui   import QPixmap, QImage, QFont, QPainter, QColor
from pathlib import Path


class PreviewDialog(QDialog):
    def __init__(self, parent, file_path, lang="he", print_option=None):
        super().__init__(parent)
        self.file_path    = file_path
        self.lang         = lang
        self.opt          = print_option or {}
        self.pages        = []        # fitz pages or QPixmap list
        self.cur_page     = 0
        self._fitz_doc    = None
        self._scale       = 1.0
        self._auto_fitted = False

        self.setWindowTitle(("תצוגה מקדימה" if lang=="he" else "Preview") +
                            f" — {Path(file_path).name}")
        self.setMinimumSize(680, 780)
        self.resize(760, 840)
        self._build_ui()
        self._load_document()

    def T(self, he, en): return he if self.lang=="he" else en

    def _build_ui(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────────
        top = QWidget(); top.setStyleSheet("background:#4a7c59;"); top.setFixedHeight(46)
        tl  = QHBoxLayout(top); tl.setContentsMargins(10,0,10,0); tl.setSpacing(6)

        def tool_btn(label, slot, w=32):
            b=QPushButton(label); b.setFixedSize(w,32)
            b.setStyleSheet("QPushButton{background:rgba(255,255,255,0.18);color:white;border:none;border-radius:6px;font-size:13px;}QPushButton:hover{background:rgba(255,255,255,0.32);}QPushButton:disabled{color:rgba(255,255,255,0.35);}")
            b.clicked.connect(slot); return b

        self._btn_pp = tool_btn("◀", lambda: self._go(-1))
        self._page_l = QLabel(""); self._page_l.setStyleSheet("color:white;font-size:12px;"); self._page_l.setAlignment(Qt.AlignmentFlag.AlignCenter); self._page_l.setFixedWidth(80)
        self._btn_np = tool_btn("▶", lambda: self._go(1))

        self._btn_zo = tool_btn("−", lambda: self._zoom(-0.15))
        self._zoom_l = QLabel("100%"); self._zoom_l.setStyleSheet("color:white;font-size:12px;"); self._zoom_l.setAlignment(Qt.AlignmentFlag.AlignCenter); self._zoom_l.setFixedWidth(46)
        self._btn_zi = tool_btn("+", lambda: self._zoom(0.15))
        self._btn_ft = tool_btn(self.T("התאם","Fit"), self._fit_to_window, w=44)

        self._title_l = QLabel(Path(self.file_path).name)
        self._title_l.setStyleSheet("color:rgba(255,255,255,0.75);font-size:11px;")
        self._title_l.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        close_b = tool_btn(self.T("סגור","Close"), self.close, w=52)

        for w in [self._btn_pp, self._page_l, self._btn_np, self._btn_zo,
                  self._zoom_l, self._btn_zi, self._btn_ft, self._title_l, close_b]:
            tl.addWidget(w)
        vl.addWidget(top)

        # ── Scroll area ──────────────────────────────────────────────────
        self._scroll = QScrollArea(); self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setStyleSheet("QScrollArea{background:#3a3835;border:none;}")
        self._canvas = QLabel(); self._canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._canvas.setStyleSheet("background:#3a3835;")
        self._scroll.setWidget(self._canvas)
        self._scroll.setWidgetResizable(False)
        vl.addWidget(self._scroll, 1)

        # ── Status bar ───────────────────────────────────────────────────
        self._status = QLabel(self.T("טוען...","Loading..."))
        self._status.setFixedHeight(24); self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("background:#2a2826;color:#8a8480;font-size:11px;")
        vl.addWidget(self._status)

    def _load_document(self):
        try:
            import fitz
            self._fitz_doc = fitz.open(self.file_path)
            self.pages = list(range(len(self._fitz_doc)))
            self._status.setText(self.T(f"{len(self.pages)} עמודים",f"{len(self.pages)} pages"))
            self._render_page(0)
        except ImportError:
            self._status.setText(self.T("התקן PyMuPDF: pip install PyMuPDF","Install PyMuPDF: pip install PyMuPDF"))
        except Exception:
            # Try as image
            pix = QPixmap(self.file_path)
            if not pix.isNull():
                self.pages = [pix]; self._render_image(pix)
            else:
                self._status.setText(self.T("לא ניתן לטעון","Cannot load file"))

    # ── Fix #6: Auto-fit on first load ──────────────────────────────────
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self._auto_fitted and self.pages:
            self._fit_to_window()

    def _fit_to_window(self):
        """Scale so the rendered page fits the scroll area viewport."""
        if not self.pages or self._fitz_doc is None: return
        import fitz
        page = self._fitz_doc.load_page(0)
        pw   = page.rect.width; ph = page.rect.height
        aw   = max(self._scroll.viewport().width()-20, 200)
        ah   = max(self._scroll.viewport().height()-20, 200)
        # fit width and height
        self._scale = min(aw/pw, ah/ph) * 0.96
        self._scale = max(0.2, min(4.0, self._scale))
        self._auto_fitted = True
        self._zoom_l.setText(f"{int(self._scale*100)}%")
        self._render_page(self.cur_page)

    def _render_page(self, idx):
        if self._fitz_doc is None or idx<0 or idx>=len(self.pages): return
        import fitz
        self.cur_page = idx
        opt_id = self.opt.get("id","normal")

        page = self._fitz_doc.load_page(idx)
        mat  = fitz.Matrix(self._scale*2, self._scale*2)

        # ── Apply print layout to preview ──────────────────────────────
        if opt_id in ("two_up","four_up","booklet_he","booklet_en"):
            # Render multiple pages on one sheet
            n = 4 if opt_id=="four_up" else 2
            self._render_nup(idx, n, opt_id)
            return
        elif opt_id == "landscape":
            # Rotate 90°
            mat = fitz.Matrix(self._scale*2, self._scale*2).prerotate(90)
        elif opt_id == "duplex":
            # Show current page normally (can't show both sides simultaneously)
            pass

        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        qpix = QPixmap.fromImage(img)
        self._canvas.setPixmap(qpix); self._canvas.setFixedSize(qpix.size())
        self._update_nav()

    def _render_nup(self, base_idx, n, opt_id):
        """Render n pages combined onto one canvas."""
        if self._fitz_doc is None: return
        import fitz

        total = len(self.pages)
        page_w = self._fitz_doc.load_page(0).rect.width
        page_h = self._fitz_doc.load_page(0).rect.height
        scale  = self._scale * 2

        cols = 2; rows = n//2 if n>2 else 1
        if n==4: rows=2

        cell_w = int(page_w * scale / cols)
        cell_h = int(page_h * scale / rows)
        canvas_w = cell_w * cols; canvas_h = cell_h * rows

        result = QPixmap(canvas_w, canvas_h)
        result.fill(QColor("#ffffff"))
        painter = QPainter(result)

        for i in range(n):
            pg_idx = base_idx + i
            if pg_idx >= total: break
            page = self._fitz_doc.load_page(pg_idx)
            mat  = fitz.Matrix(scale/cols, scale/rows)
            pix  = page.get_pixmap(matrix=mat, alpha=False)
            img  = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            qpix = QPixmap.fromImage(img)

            # Position: RTL for Hebrew booklet
            if opt_id=="booklet_he":
                col = (n-1-i) % cols
            else:
                col = i % cols
            row = i // cols
            x = col * cell_w; y = row * cell_h
            painter.drawPixmap(x, y, qpix)

        painter.end()
        self._canvas.setPixmap(result); self._canvas.setFixedSize(result.size())
        self._update_nav()

    def _render_image(self, pix):
        scaled = pix.scaled(
            int(pix.width()*self._scale), int(pix.height()*self._scale),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._canvas.setPixmap(scaled); self._canvas.setFixedSize(scaled.size())
        self._page_l.setText("1 / 1")
        self._btn_pp.setEnabled(False); self._btn_np.setEnabled(False)

    def _update_nav(self):
        total = len(self.pages)
        self._page_l.setText(f"{self.cur_page+1} / {total}")
        self._btn_pp.setEnabled(self.cur_page > 0)
        self._btn_np.setEnabled(self.cur_page < total-1)
        self._zoom_l.setText(f"{int(self._scale*100)}%")

    def _go(self, delta):
        new = self.cur_page + delta
        if 0 <= new < len(self.pages):
            if self._fitz_doc: self._render_page(new)
            elif self.pages and isinstance(self.pages[0], QPixmap):
                self._render_image(self.pages[0])

    def _zoom(self, delta):
        self._scale = max(0.2, min(4.0, self._scale+delta))
        self._auto_fitted = False
        if self._fitz_doc: self._render_page(self.cur_page)
        elif self.pages and isinstance(self.pages[0], QPixmap):
            self._render_image(self.pages[0])
