"""共享的自定义组件"""

from PyQt6.QtWidgets import QLineEdit, QTextEdit, QMenu
from PyQt6.QtCore import Qt


class CLineEdit(QLineEdit):
    """带中文右键菜单的输入框"""

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        for action in menu.actions():
            text = action.text()
            if text == "Undo":
                action.setText("撤销")
            elif text == "Redo":
                action.setText("重做")
            elif text == "Cut":
                action.setText("剪切")
            elif text == "Copy":
                action.setText("复制")
            elif text == "Paste":
                action.setText("粘贴")
            elif text == "Delete":
                action.setText("删除")
            elif text == "Select All":
                action.setText("全选")
        menu.exec(event.globalPos())


class CTextEdit(QTextEdit):
    """带中文右键菜单的文本编辑框"""

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        for action in menu.actions():
            text = action.text()
            if text == "Undo":
                action.setText("撤销")
            elif text == "Redo":
                action.setText("重做")
            elif text == "Cut":
                action.setText("剪切")
            elif text == "Copy":
                action.setText("复制")
            elif text == "Paste":
                action.setText("粘贴")
            elif text == "Delete":
                action.setText("删除")
            elif text == "Select All":
                action.setText("全选")
        menu.exec(event.globalPos())
