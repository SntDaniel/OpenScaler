# 包含 MainWindow 类，负责主界面布局和菜单
# 包含 MainWindow 类，负责主界面布局和菜单
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QPushButton,
    QVBoxLayout, QWidget, QHBoxLayout, QScrollArea, QButtonGroup, QRadioButton, QDialog, QFormLayout, QComboBox
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from PySide6.QtPrintSupport import QPrinter

from image_label import ImageLabel


class PaperSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("页面设置")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        # 纸张尺寸选择
        self.paper_size_combo = QComboBox()
        # 添加标准纸张尺寸 (宽x高 mm)
        paper_sizes = {
            "A4": (210, 297),
            "A3": (297, 420),
            "A5": (148, 210),
            "Letter": (216, 279),
            "Legal": (216, 356)
        }
        for name, size in paper_sizes.items():
            self.paper_size_combo.addItem(name, size)
        
        # 默认选择A4
        self.paper_size_combo.setCurrentText("A4")
        
        # 方向选择
        self.portrait_radio = QRadioButton("纵向")
        self.landscape_radio = QRadioButton("横向")
        self.portrait_radio.setChecked(True)
        
        orientation_group = QButtonGroup(self)
        orientation_group.addButton(self.portrait_radio)
        orientation_group.addButton(self.landscape_radio)
        
        orientation_layout = QHBoxLayout()
        orientation_layout.addWidget(self.portrait_radio)
        orientation_layout.addWidget(self.landscape_radio)
        
        layout.addRow("纸张尺寸:", self.paper_size_combo)
        layout.addRow("方向:", orientation_layout)
        
        # 添加确定和取消按钮
        buttons = QHBoxLayout()
        from PySide6.QtWidgets import QPushButton, QDialogButtonBox
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)
        
    def get_settings(self):
        size_name = self.paper_size_combo.currentText()
        size_data = self.paper_size_combo.currentData()
        is_portrait = self.portrait_radio.isChecked()
        
        # 如果是横向，交换宽高
        if not is_portrait:
            size_data = (size_data[1], size_data[0])
            
        return {
            "size_name": size_name,
            "width_mm": size_data[0],
            "height_mm": size_data[1],
            "is_portrait": is_portrait
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenScaler")

        self.image_loaded = False
        
        # 默认纸张设置 (A4 纵向)
        self.paper_settings = {
            "size_name": "A4",
            "width_mm": 210,
            "height_mm": 297,
            "is_portrait": True
        }

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
        
        # 添加导出PDF功能
        export_pdf = QAction("导出为PDF", self)
        export_pdf.triggered.connect(self.export_pdf)
        fm.addAction(export_pdf)

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
        
        # 页面设置菜单
        page_menu = menubar.addMenu("页面")
        page_setup = QAction("页面设置", self)
        page_setup.triggered.connect(self.page_setup)
        page_menu.addAction(page_setup)

        mm = menubar.addMenu("添加测量")
        sa = QAction("单线测量", self)
        sa.triggered.connect(self.enable_single)
        ga = QAction("平行线测量", self)
        ga.triggered.connect(self.enable_gradient)
        mm.addAction(sa)
        mm.addAction(ga)

        self.statusBar().showMessage("缩放: 100%")
        self.image_label.scale_changed.connect(self.update_statusbar)
        # 传递纸张设置给image_label
        self.image_label.set_paper_settings(self.paper_settings)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.bmp *.jpeg)")
        if file:  # 用户选择了文件
            self.image_label.load_image_on_paper(file, self.paper_settings)
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
        
    def page_setup(self):
        dialog = PaperSettingsDialog(self)
        # 设置当前值
        dialog.paper_size_combo.setCurrentText(self.paper_settings["size_name"])
        if self.paper_settings["is_portrait"]:
            dialog.portrait_radio.setChecked(True)
        else:
            dialog.landscape_radio.setChecked(True)
            
        if dialog.exec() == QDialog.Accepted:
            self.paper_settings = dialog.get_settings()
            self.image_label.set_paper_settings(self.paper_settings)
            # 如果已经加载了图片，重新加载以适应新设置
            if self.image_loaded:
                self.image_label.reload_image_on_paper(self.paper_settings)
            self.statusBar().showMessage(f"页面设置已更新: {self.paper_settings['size_name']} { '纵向' if self.paper_settings['is_portrait'] else '横向'}")

    def export_pdf(self):
        if not self.image_loaded:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "导出失败", "请先加载图片")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "导出为PDF", "", "PDF Files (*.pdf)")
        if file_path:
            if self.image_label.export_to_pdf(file_path, self.paper_settings):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "导出成功", f"PDF文件已保存到: {file_path}")
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "导出失败", "导出PDF时发生错误")