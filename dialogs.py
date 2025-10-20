# 包含所有对话框类
import sys
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QHBoxLayout, QWidget,
    QLabel, QVBoxLayout, QPushButton, QFrame
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QPalette, QColor


class LengthInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("输入目标长度")
        self.setModal(True)
        self.setFixedSize(300, 120)
        
        layout = QFormLayout(self)
        
        # 创建包含数值输入和单位选择的水平布局
        input_layout = QHBoxLayout()
        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("输入目标长度（mm）")
        
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["mm", "cm", "inch"])
        self.unit_combo.setCurrentText("mm")  # 默认单位为mm
        
        input_layout.addWidget(self.length_input)
        input_layout.addWidget(self.unit_combo)
        
        # 创建一个容器widget来容纳水平布局
        input_widget = QWidget()
        input_widget.setLayout(input_layout)
        
        layout.addRow("目标长度:", input_widget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        
    def get_length(self):
        return self.length_input.text()
        
    def get_unit(self):
        return self.unit_combo.currentText()
        
    def set_length(self, length):
        self.length_input.setText(length)
        
    def set_unit(self, unit):
        self.unit_combo.setCurrentText(unit)


class MoveImageTipDialog(QDialog):
    """
    显示"移动图片"提示的对话框，1秒后淡出
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # 设置窗口位置和大小
        self.setFixedSize(200, 100)
        
        # 创建主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建提示框容器
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 50);
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        
        # 提示文本
        label = QLabel("移动图片")
        label.setStyleSheet("color: white; font-size: 16px;")
        label.setAlignment(Qt.AlignCenter)
        
        # 确认按钮
        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        self.confirm_btn.clicked.connect(self.accept)
        
        container_layout.addWidget(label)
        container_layout.addWidget(self.confirm_btn)
        
        layout.addWidget(container)
        self.setLayout(layout)
        
        # 设置淡出动画
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(1000)  # 1秒淡出
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.OutQuad)
        self.fade_animation.finished.connect(self.close)
        
        # 设置定时器，1秒后开始淡出
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade_out)
        
    def showEvent(self, event):
        super().showEvent(event)
        # 显示1秒后开始淡出
        self.timer.start(1000)
        
    def start_fade_out(self):
        self.fade_animation.start()
        
    def mousePressEvent(self, event):
        # 点击任意位置关闭对话框
        self.accept()