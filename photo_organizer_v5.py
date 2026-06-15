# -*- coding: utf-8 -*-
"""
picsort - Photo/Video Organizer v1.0.1
Automatically sort photos and videos by capture date into year/month/day structure
"""

import os
import sys
import shutil
import struct
import datetime
import threading
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QProgressBar,
    QGroupBox, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont

# ============================================================
# 常量定义
# ============================================================

PHOTO_EXTS = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
ANIMATED_EXTS = {'.gif'}
VIDEO_EXTS = {'.mp4', '.mov', '.m4v', '.avi', '.flv', '.wmv', '.3gp'}
ALL_SUPPORTED = PHOTO_EXTS | ANIMATED_EXTS | VIDEO_EXTS


# ============================================================
# 元数据读取工具
# ============================================================

def get_exif_datetime(filepath):
    """从照片 EXIF 中读取拍摄日期时间"""
    try:
        from PIL import Image
        img = Image.open(filepath)
        exif_data = img.getexif()
        if not exif_data:
            return None
        for tag_id in [0x9003, 0x0132, 0x9004]:
            val = exif_data.get(tag_id)
            if val:
                try:
                    return datetime.datetime.strptime(val.strip(), "%Y:%m:%d %H:%M:%S")
                except (ValueError, AttributeError):
                    continue
        ifd = exif_data.get_ifd(0x8769)
        if ifd:
            for tag_id in [0x9003, 0x0132, 0x9004]:
                val = ifd.get(tag_id)
                if val:
                    try:
                        return datetime.datetime.strptime(val.strip(), "%Y:%m:%d %H:%M:%S")
                    except (ValueError, AttributeError):
                        continue
        return None
    except Exception:
        return None


def _parse_mp4_box_header(f):
    """读取 MP4 box 头部"""
    header = f.read(8)
    if len(header) < 8:
        return None, 0, 8
    box_size = struct.unpack('>I', header[:4])[0]
    box_type = header[4:8]
    if box_size == 1:
        ext = f.read(8)
        if len(ext) < 8:
            return None, 0, 16
        box_size = struct.unpack('>Q', ext)[0]
        return box_type, box_size, 16
    if box_size == 0:
        return box_type, 0, 8
    return box_type, box_size, 8


def get_mp4_creation_time(filepath):
    """从 MP4 文件读取创建时间"""
    try:
        file_size = os.path.getsize(filepath)
        with open(filepath, 'rb') as f:
            while f.tell() < file_size:
                box_type, box_size, header_size = _parse_mp4_box_header(f)
                if box_type is None:
                    break
                if box_size == 0:
                    box_size = file_size - f.tell() + header_size
                if box_size < header_size:
                    break
                box_start = f.tell() - header_size
                if box_type == b'moov':
                    moov_end = box_start + box_size
                    while f.tell() < moov_end:
                        inner_type, inner_size, inner_header = _parse_mp4_box_header(f)
                        if inner_type is None:
                            break
                        if inner_size == 0:
                            inner_size = moov_end - f.tell() + inner_header
                        if inner_size < inner_header:
                            break
                        if inner_type == b'mvhd':
                            mvhd_data = f.read(inner_size - inner_header)
                            if len(mvhd_data) >= 8:
                                version = mvhd_data[0]
                                ct = struct.unpack('>I' if version == 0 else '>Q',
                                                   mvhd_data[4:8] if version == 0 else mvhd_data[4:12])[0]
                                try:
                                    dt = datetime.datetime(1904, 1, 1) + datetime.timedelta(seconds=ct)
                                    if dt.year >= 1970:
                                        return dt
                                except (OverflowError, ValueError, OSError):
                                    pass
                        else:
                            f.seek(inner_size - inner_header, 1)
                else:
                    f.seek(box_start + box_size)
    except Exception:
        pass
    return None


def get_quicktime_creation_time(filepath):
    """从 MOV 文件读取创建时间"""
    return get_mp4_creation_time(filepath)


def get_file_modified_time(filepath):
    """获取文件修改时间"""
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
    except Exception:
        return None


def get_media_datetime(filepath, ext):
    """根据文件类型获取拍摄/创建时间"""
    dt = None
    if ext in PHOTO_EXTS or ext in ANIMATED_EXTS:
        dt = get_exif_datetime(filepath)
    if dt is None and ext in VIDEO_EXTS:
        if ext in ('.mp4', '.m4v', '.3gp'):
            dt = get_mp4_creation_time(filepath)
        elif ext == '.mov':
            dt = get_quicktime_creation_time(filepath)
    if dt is None:
        dt = get_file_modified_time(filepath)
    return dt


# ============================================================
# 目录结构生成
# ============================================================

def build_directory_path(target_dir, dt, level1, level2, level3):
    """根据配置生成目录路径"""
    parts = []
    desc_parts = []
    for level in [level1, level2, level3]:
        if level == 'year':
            parts.append(f"{dt.year:04d}")
            desc_parts.append(f"{dt.year:04d}")
        elif level == 'month':
            parts.append(f"{dt.month:02d}")
            desc_parts.append(f"{dt.month:02d}")
        elif level == 'day':
            parts.append(f"{dt.day:02d}")
            desc_parts.append(f"{dt.day:02d}")
    if parts:
        return os.path.join(target_dir, *parts), "/".join(desc_parts)
    return target_dir, "(根目录)"


def get_path_preview(level1, level2, level3):
    """生成路径预览"""
    parts = []
    for level in [level1, level2, level3]:
        if level == 'year':
            parts.append("2025")
        elif level == 'month':
            parts.append("06")
        elif level == 'day':
            parts.append("15")
    return "目标文件夹/" + "/".join(parts) + "/照片.jpg" if parts else "目标文件夹/照片.jpg"


# ============================================================
# 文件整理核心逻辑
# ============================================================

def collect_files(source_dir):
    """递归收集媒体文件"""
    files = []
    for root, dirs, filenames in os.walk(source_dir):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in ALL_SUPPORTED:
                files.append(os.path.join(root, fname))
    return files


def organize_files(source_dir, target_dir, level1, level2, level3, progress_callback=None):
    """整理文件"""
    files = collect_files(source_dir)
    total = len(files)
    success, skip = 0, 0

    for i, filepath in enumerate(files):
        fname = os.path.basename(filepath)
        ext = os.path.splitext(fname)[1].lower()

        if progress_callback:
            progress_callback(i, total, fname, "处理中...")

        dt = get_media_datetime(filepath, ext)
        if dt is None:
            skip += 1
            if progress_callback:
                progress_callback(i + 1, total, fname, "跳过：无法获取时间")
            continue

        dest_dir, path_desc = build_directory_path(target_dir, dt, level1, level2, level3)
        dest_path = os.path.join(dest_dir, fname)

        if os.path.exists(dest_path):
            skip += 1
            if progress_callback:
                progress_callback(i + 1, total, fname, "跳过：已存在")
            continue

        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(filepath, dest_path)
            success += 1
            if progress_callback:
                progress_callback(i + 1, total, fname, f"→ {path_desc}/")
        except Exception as e:
            skip += 1
            if progress_callback:
                progress_callback(i + 1, total, fname, f"跳过：{e}")

    empty_removed = remove_empty_folders(source_dir)
    return success, skip, empty_removed


def remove_empty_folders(root_dir):
    """删除空文件夹"""
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        if dirpath == root_dir:
            continue
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
                removed += 1
        except OSError:
            pass
    return removed


# ============================================================
# 信号类
# ============================================================

class WorkerSignals(QObject):
    progress = pyqtSignal(int, int, str, str)
    finished = pyqtSignal(int, int, int)
    error = pyqtSignal(str)


# ============================================================
# GUI 界面
# ============================================================

class PhotoOrganizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("picsort")
        self.setMinimumSize(620, 500)
        self.resize(620, 520)
        self.setCentralWidget(QWidget())

        self.source_dir = ""
        self.target_dir = ""
        self.is_running = False
        self.signals = WorkerSignals()

        self.signals.progress.connect(self._update_progress)
        self.signals.finished.connect(self._show_result)
        self.signals.error.connect(self._show_error)

        self._build_ui()
        self._center_window()

    def _center_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def _build_ui(self):
        layout = QVBoxLayout(self.centralWidget())
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)

        title = QLabel("� picsort")
        title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("按拍摄时间自动分类归档，支持自定义目录层级")
        desc.setFont(QFont("Microsoft YaHei UI", 9))
        desc.setStyleSheet("color: gray;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # 源文件夹
        src_group = QGroupBox("📂 源文件夹")
        src_layout = QHBoxLayout(src_group)
        self.src_edit = QLineEdit()
        self.src_edit.setReadOnly(True)
        self.src_edit.setPlaceholderText("请选择...")
        src_layout.addWidget(self.src_edit)
        src_btn = QPushButton("选择")
        src_btn.clicked.connect(self._select_source)
        src_layout.addWidget(src_btn)
        layout.addWidget(src_group)

        # 目标文件夹
        tgt_group = QGroupBox("📁 目标文件夹")
        tgt_layout = QHBoxLayout(tgt_group)
        self.tgt_edit = QLineEdit()
        self.tgt_edit.setReadOnly(True)
        self.tgt_edit.setPlaceholderText("请选择...")
        tgt_layout.addWidget(self.tgt_edit)
        tgt_btn = QPushButton("选择")
        tgt_btn.clicked.connect(self._select_target)
        tgt_layout.addWidget(tgt_btn)
        layout.addWidget(tgt_group)

        # 目录配置 - 水平排列
        dir_group = QGroupBox("📂 目录结构")
        dir_layout = QVBoxLayout(dir_group)
        font = QFont("Microsoft YaHei UI", 9)

        combo_row = QHBoxLayout()
        for label_text, attr, default in [("一级:", "level1", 0), ("二级:", "level2", 1), ("三级:", "level3", 3)]:
            label = QLabel(label_text)
            label.setFont(font)
            combo_row.addWidget(label)
            combo = QComboBox()
            combo.setFont(font)
            combo.addItems(["年", "月", "日", "无"])
            combo.setCurrentIndex(default)
            combo.currentIndexChanged.connect(self._update_preview)
            setattr(self, f"{attr}_combo", combo)
            combo_row.addWidget(combo)
        combo_row.addStretch()
        dir_layout.addLayout(combo_row)

        preview_row = QHBoxLayout()
        preview_label = QLabel("预览:")
        preview_label.setFont(font)
        preview_row.addWidget(preview_label)
        self.preview_label = QLabel("目标文件夹/2025/06/照片.jpg")
        self.preview_label.setFont(font)
        self.preview_label.setStyleSheet("color: #0066cc;")
        preview_row.addWidget(self.preview_label, 1)
        dir_layout.addLayout(preview_row)
        layout.addWidget(dir_group)

        # 进度
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        self.status_label.setFont(font)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(40)
        progress_layout.addWidget(self.status_label)
        layout.addWidget(progress_group)

        self.stats_label = QLabel("")
        self.stats_label.setFont(font)
        self.stats_label.setStyleSheet("color: #555;")
        layout.addWidget(self.stats_label)

        layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("🚀 开始整理")
        self.start_btn.setMinimumHeight(35)
        self.start_btn.clicked.connect(self._start_organize)
        btn_layout.addWidget(self.start_btn)
        close_btn = QPushButton("退出")
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _update_preview(self):
        mapping = {0: 'year', 1: 'month', 2: 'day', 3: 'none'}
        self.preview_label.setText(get_path_preview(
            mapping[self.level1_combo.currentIndex()],
            mapping[self.level2_combo.currentIndex()],
            mapping[self.level3_combo.currentIndex()]))

    def _select_source(self):
        path = QFileDialog.getExistingDirectory(self, "选择源文件夹")
        if path:
            self.source_dir = path
            self.src_edit.setText(path)

    def _select_target(self):
        path = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if path:
            self.target_dir = path
            self.tgt_edit.setText(path)

    def _update_progress(self, current, total, filename, message):
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.status_label.setText(f"[{current}/{total}] {filename} {message}")

    def _start_organize(self):
        if self.is_running:
            return
        if not self.source_dir:
            QMessageBox.warning(self, "提示", "请选择源文件夹！")
            return
        if not self.target_dir:
            QMessageBox.warning(self, "提示", "请选择目标文件夹！")
            return

        mapping = {0: 'year', 1: 'month', 2: 'day', 3: 'none'}
        l1, l2, l3 = mapping[self.level1_combo.currentIndex()], mapping[self.level2_combo.currentIndex()], mapping[self.level3_combo.currentIndex()]

        if l1 == l2 == l3 == 'none':
            QMessageBox.warning(self, "提示", "请至少设置一个目录层级！")
            return

        if QMessageBox.question(self, "确认", f"文件将被移动到目标文件夹，确认继续？", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        self.is_running = True
        self.start_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.stats_label.setText("")

        thread = threading.Thread(target=self._do_organize, args=(self.source_dir, self.target_dir, l1, l2, l3), daemon=True)
        thread.start()

    def _do_organize(self, source, target, l1, l2, l3):
        try:
            success, skip, empty = organize_files(source, target, l1, l2, l3,
                                                   lambda c, t, f, m: self.signals.progress.emit(c, t, f, m))
            self.signals.finished.emit(success, skip, empty)
        except Exception as e:
            self.signals.error.emit(str(e))

    def _show_result(self, success, skip, empty):
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText("✅ 完成！")
        self.stats_label.setText(f"成功: {success} | 跳过: {skip} | 删除空文件夹: {empty}")
        QMessageBox.information(self, "完成", f"✅ 成功: {success}\n⏭️ 跳过: {skip}\n🗑️ 删除空文件夹: {empty}")

    def _show_error(self, msg):
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.status_label.setText("❌ 出错")
        QMessageBox.critical(self, "错误", msg)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PhotoOrganizerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
