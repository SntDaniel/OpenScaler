# 包含所有对话框类
import sys
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox
)
from PySide6.QtCore import Qt


class LengthInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("输入目标长度")
        self.setModal(True)
        self.setFixedSize(250, 100)
        
        layout = QFormLayout(self)
        
        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("输入目标长度（mm）")  # 修改占位符文本
        
        layout.addRow("目标长度:", self.length_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        
    def get_length(self):
        return self.length_input.text()
        
    def set_length(self, length):
        self.length_input.setText(length)