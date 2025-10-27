# 包含 MainWindow 类，负责主界面布局和菜单
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QPushButton,
    QVBoxLayout, QWidget, QHBoxLayout, QScrollArea, QButtonGroup, QRadioButton, QDialog, QFormLayout, QComboBox, QMenu
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

        self.btn_confirm = QPushButton("确认画线")
        self.btn_confirm.clicked.connect(self.image_label.confirm_line)
        self.btn_confirm.hide()
        self.image_label.btn_confirm = self.btn_confirm
        
        # 添加图片移动确认按钮
        self.btn_confirm_move = QPushButton("确认移动")
        self.btn_confirm_move.clicked.connect(self.confirm_image_move)
        self.btn_confirm_move.hide()
        self.image_label.btn_confirm_move = self.btn_confirm_move

        # 添加照片按钮
        self.btn_add_photo = QPushButton("添加照片")
        self.btn_add_photo.setFixedSize(200, 60)
        self.btn_add_photo.setStyleSheet("font-size:20px;")
        self.btn_add_photo.clicked.connect(self.load_image)

        bl = QHBoxLayout()
        bl.addWidget(self.btn_confirm)
        bl.addWidget(self.btn_confirm_move)

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
        zai.triggered.connect(lambda: self.image_label.apply_zoom(1.1, self.image_label.rect().center()))
        zao = QAction("缩小", self)
        zao.triggered.connect(lambda: self.image_label.apply_zoom(0.9, self.image_label.rect().center()))
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
        
        # 移动图片菜单项（第一级菜单）
        self.move_image_action = QAction("移动图片", self)
        self.move_image_action.setCheckable(True)
        self.move_image_action.triggered.connect(self.toggle_image_move)
        menubar.addAction(self.move_image_action)

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
            # 不再隐藏btn_confirm_move，因为load_image_on_paper会自动显示它
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
        self.btn_confirm_move.hide()
        # 退出移动模式
        self.move_image_action.setChecked(False)
        self.image_label.set_image_move_mode(False)

    def enable_gradient(self):
        self.image_label.set_drawing_enabled(True, mode="gradient", clear_previous=True)
        self.btn_confirm.show()
        self.btn_confirm_move.hide()
        # 退出移动模式
        self.move_image_action.setChecked(False)
        self.image_label.set_image_move_mode(False)

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
                
    def toggle_image_move(self, checked):
        """切换图片移动模式"""
        self.image_label.set_image_move_mode(checked)
        if checked:
            self.btn_confirm_move.show()
            self.btn_confirm.hide()
            self.statusBar().showMessage("图片移动模式: 点击并拖拽图片来移动位置，点击确认移动完成")
        else:
            self.btn_confirm_move.hide()
            self.statusBar().showMessage("已退出图片移动模式")

    def confirm_image_move(self):
        """确认图片移动"""
        # 退出移动模式
        self.move_image_action.setChecked(False)
        self.image_label.set_image_move_mode(False)
        self.btn_confirm_move.hide()
        self.statusBar().showMessage("图片移动已完成")