# 包含所有对话框类
import sys
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QHBoxLayout, QWidget
)
from PySide6.QtCore import Qt


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