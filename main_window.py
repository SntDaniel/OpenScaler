# 包含 MainWindow 类，负责主界面布局和菜单
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QPushButton,
    QVBoxLayout, QWidget, QHBoxLayout, QScrollArea
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from image_label import ImageLabel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenScaler")

        self.image_loaded = False

        self.image_label = ImageLabel()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.btn_confirm = QPushButton("确认")
        self.btn_confirm.clicked.connect(self.image_label.confirm_line)
        self.btn_confirm.hide()
        self.image_label.btn_confirm = self.btn_confirm

        # 添加照片按钮
        self.btn_add_photo = QPushButton("添加照片")
        self.btn_add_photo.setFixedSize(200, 60)
        self.btn_add_photo.setStyleSheet("font-size:20px;")
        self.btn_add_photo.clicked.connect(self.load_image)

        bl = QHBoxLayout()
        bl.addWidget(self.btn_confirm)

        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.addLayout(bl)

        c = QWidget()
        c.setLayout(layout)
        self.setCentralWidget(c)

        # overlay 界面，按钮居中
        self.overlay = QWidget(self)
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.addStretch()
        overlay_layout.addWidget(self.btn_add_photo, alignment=Qt.AlignCenter)
        overlay_layout.addStretch()
        self.overlay.setLayout(overlay_layout)
        self.overlay.setGeometry(self.rect())
        self.overlay.show()

        menubar = self.menuBar()
        fm = menubar.addMenu("文件")
        oa = QAction("打开图片", self)
        oa.triggered.connect(self.load_image)
        fm.addAction(oa)

        vm = menubar.addMenu("视图")
        zai = QAction("放大", self)
        zai.triggered.connect(lambda: self.image_label.apply_zoom(1.25, self.image_label.rect().center()))
        zao = QAction("缩小", self)
        zao.triggered.connect(lambda: self.image_label.apply_zoom(0.8, self.image_label.rect().center()))
        zr = QAction("还原", self)
        zr.triggered.connect(self.image_label.reset_zoom)
        vm.addAction(zai)
        vm.addAction(zao)
        vm.addAction(zr)

        mm = menubar.addMenu("添加测量")
        sa = QAction("单线测量", self)
        sa.triggered.connect(self.enable_single)
        ga = QAction("平行线测量", self)
        ga.triggered.connect(self.enable_gradient)
        mm.addAction(sa)
        mm.addAction(ga)

        self.statusBar().showMessage("缩放: 100%")
        self.image_label.scale_changed.connect(self.update_statusbar)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.bmp *.jpeg)")
        if file:  # 用户选择了文件
            self.image_label.load_image(file)
            self.btn_confirm.hide()
            self.overlay.hide()
            self.image_loaded = True
        else:  # 用户取消
            if not self.image_loaded:
                self.overlay.show()   # 只在从未加载过图片时，才显示按钮
            else:
                self.overlay.hide()   # 已经加载过，就保持隐藏

    def enable_single(self):
        self.image_label.set_drawing_enabled(True, mode="single", clear_previous=True)
        self.btn_confirm.show()

    def enable_gradient(self):
        self.image_label.set_drawing_enabled(True, mode="gradient", clear_previous=True)
        self.btn_confirm.show()

    def update_statusbar(self, factor):
        self.statusBar().showMessage(f"缩放: {int(factor*100)}%")