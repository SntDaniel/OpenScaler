# 包含 MainWindow 类，负责主界面布局和菜单 
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QPushButton,
    QVBoxLayout, QWidget, QHBoxLayout, QScrollArea, QButtonGroup, QRadioButton, QDialog, QFormLayout, QComboBox, QMenu
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QRect
from image_label import ImageLabel


# ================== 按钮样式 ==================
# 替换原有的 save_button_style 定义
save_button_style = """
    QPushButton {
        background-color: qlineargradient(
            spread:pad, x1:0, y1:0, x2:0, y2:1,
            stop:0 #4caf65, stop:1 #2e637d
        );
        color: white;
        font-size: 20px;
        font-weight: bold;
        padding: 12px 28px;
        border: none;
        border-radius: 25px;
    }
    QPushButton:hover {
        background-color: qlineargradient(
            spread:pad, x1:0, y1:0, x2:0, y2:1,
            stop:0 #5fcf76, stop:1 #3b6f9d
        );
        padding: 12px 28px;  /* 保持与正常状态相同的padding */
    }
    QPushButton:pressed {
        background-color: #1f4b5d;
        padding: 13px 26px;
    }
"""
# =============================================


class PaperSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("纸张设置")
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
        from PySide6.QtWidgets import QPushButton
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")

        # 应用按钮样式
        # ok_button.setStyleSheet(save_button_style)
        # cancel_button.setStyleSheet(save_button_style)

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


class FloatingButtonWidget(QWidget):
    """浮动按钮控件，用于显示确认按钮"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 设置背景为透明
        self.setStyleSheet("background-color: transparent;")
        
        # 创建按钮布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.btn_confirm = QPushButton("确认画线")
        self.btn_confirm_move = QPushButton("确认位置")
        self.btn_confirm_move.hide()

        # 应用统一按钮样式
        self.btn_confirm.setStyleSheet(save_button_style)
        self.btn_confirm_move.setStyleSheet(save_button_style)
        
        layout.addWidget(self.btn_confirm)
        layout.addWidget(self.btn_confirm_move)
        self.btn_confirm.setAutoDefault(True)  # 允许通过Enter键触发
        self.btn_confirm.setDefault(False)     # 但不默认设置为默认按钮

        self.btn_confirm_move.setAutoDefault(True)  # 允许通过Enter键触发
        self.btn_confirm_move.setDefault(False)     # 但不默认设置为默认按钮
        self.adjustSize()
        
    def move_to_bottom_center(self, parent_rect):
        """将按钮移动到父窗口的底部中央位置"""
        x = parent_rect.center().x() - self.width() // 2
        y = parent_rect.bottom() - self.height() - 20  # 距离底部20像素
        self.move(x, y)
        
    def show_buttons(self, mode="draw"):
        """显示相应的按钮"""
        if mode == "draw":
            self.btn_confirm.show()
            self.btn_confirm_move.hide()
        elif mode == "move":
            self.btn_confirm.hide()
            self.btn_confirm_move.show()
        self.show()
        self.raise_()
        
    def hide_buttons(self):
        """隐藏所有按钮"""
        self.hide()


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

        # 创建浮动按钮控件
        self.floating_buttons = FloatingButtonWidget(self)
        self.floating_buttons.btn_confirm.clicked.connect(self.image_label.confirm_line)
        self.floating_buttons.btn_confirm_move.clicked.connect(self.confirm_image_move)
        self.image_label.btn_confirm = self.floating_buttons.btn_confirm
        self.image_label.btn_confirm_move = self.floating_buttons.btn_confirm_move

        # 添加照片按钮
        self.btn_add_photo = QPushButton("添加照片")
        self.btn_add_photo.setFixedSize(200, 60)
        self.btn_add_photo.setStyleSheet(save_button_style)
        self.btn_add_photo.clicked.connect(self.load_image)

        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.setContentsMargins(0, 0, 0, 0)

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

        # 创建菜单栏但默认禁用
        self.create_menubar()
        self.set_menu_enabled(False)

        self.statusBar().showMessage("缩放: 100%")
        self.image_label.scale_changed.connect(self.update_statusbar)
        # 传递纸张设置给image_label
        self.image_label.set_paper_settings(self.paper_settings)


    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        fm = menubar.addMenu("文件")
        self.oa = QAction("添加图片", self)
        self.oa.triggered.connect(self.load_image)
        fm.addAction(self.oa)
        
        self.export_pdf_action = QAction("导出为PDF", self)
        self.export_pdf_action.triggered.connect(self.export_pdf)
        fm.addAction(self.export_pdf_action)

        # 页面设置菜单
        page_menu = menubar.addMenu("页面")
        self.page_setup_action = QAction("纸张设置", self)
        self.page_setup_action.triggered.connect(self.page_setup)
        page_menu.addAction(self.page_setup_action)

        mm = menubar.addMenu("添加测量")
        self.sa = QAction("单线测量", self)
        self.sa.triggered.connect(self.enable_single)
        self.ga = QAction("平行线测量", self)
        self.ga.triggered.connect(self.enable_gradient)
        mm.addAction(self.sa)
        mm.addAction(self.ga)
        
        # 移动图片菜单项（第一级菜单）
        self.move_image_action = QAction("移动图片", self)
        self.move_image_action.setCheckable(True)
        self.move_image_action.triggered.connect(self.toggle_image_move)
        menubar.addAction(self.move_image_action)

    def set_menu_enabled(self, enabled):
        """设置菜单项的启用状态"""
        self.export_pdf_action.setEnabled(enabled)
        self.page_setup_action.setEnabled(enabled)
        self.sa.setEnabled(enabled)
        self.ga.setEnabled(enabled)
        self.move_image_action.setEnabled(enabled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())
        # 更新浮动按钮位置到底部中央
        self.floating_buttons.move_to_bottom_center(self.rect())

    def moveEvent(self, event):
        super().moveEvent(event)
        # 更新浮动按钮位置到底部中央
        self.floating_buttons.move_to_bottom_center(self.rect())

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.bmp *.jpeg)")
        if file:  # 用户选择了文件
            self.image_label.load_image_on_paper(file, self.paper_settings)
            # 确保在第一次加载图片时显示移动确认按钮
            if not self.image_loaded:
                self.floating_buttons.show_buttons("move")
            else:
                self.floating_buttons.hide_buttons()
            self.overlay.hide()
            self.image_loaded = True
            
            # 第一次加载图片时启用菜单项
            if not self.export_pdf_action.isEnabled():
                self.set_menu_enabled(True)
        else:  # 用户取消
            if not self.image_loaded:
                self.overlay.show()   # 只在从未加载过图片时，才显示按钮
            else:
                self.overlay.hide()   # 已经加载过，就保持隐藏

    def keyPressEvent(self, event):
        """处理全局键盘按键事件"""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # 如果浮动按钮可见，触发相应的操作
            if self.floating_buttons.isVisible():
                if self.floating_buttons.btn_confirm.isVisible() and self.floating_buttons.btn_confirm.isEnabled():
                    self.floating_buttons.btn_confirm.click()
                    return
                elif self.floating_buttons.btn_confirm_move.isVisible() and self.floating_buttons.btn_confirm_move.isEnabled():
                    self.floating_buttons.btn_confirm_move.click()
                    return
        super().keyPressEvent(event)

    def enable_single(self):
        self.image_label.set_drawing_enabled(True, mode="single", clear_previous=True)
        self.floating_buttons.show_buttons("draw")
        # 退出移动模式
        self.move_image_action.setChecked(False)
        self.image_label.set_image_move_mode(False)
        # 设置焦点到 image_label 以便接收键盘事件
        self.image_label.setFocus()


    def enable_gradient(self):
        self.image_label.set_drawing_enabled(True, mode="gradient", clear_previous=True)
        self.floating_buttons.show_buttons("draw")
        # 退出移动模式
        self.move_image_action.setChecked(False)
        self.image_label.set_image_move_mode(False)
        # 设置焦点到 image_label 以便接收键盘事件
        self.image_label.setFocus()

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
            
        # 生成基于当前时间的默认文件名
        from datetime import datetime
        default_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "导出为PDF", default_filename, "PDF Files (*.pdf)")
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
            self.floating_buttons.show_buttons("move")
            self.statusBar().showMessage("图片移动模式: 点击并拖拽图片来移动位置，点击确认移动完成")
        else:
            self.floating_buttons.hide_buttons()
            self.statusBar().showMessage("已退出图片移动模式")

    def confirm_image_move(self):
        """确认图片移动"""
        # 退出移动模式
        self.move_image_action.setChecked(False)
        self.image_label.set_image_move_mode(False)
        self.floating_buttons.hide_buttons()
        self.statusBar().showMessage("图片移动已完成")