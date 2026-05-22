import os
from PyQt5 import QtCore, QtGui, QtWidgets
from ui.layout import Ui_Dialog

class DesignApp(QtWidgets.QDialog, Ui_Dialog):
    # Signals for threading
    chat_requested = QtCore.pyqtSignal(str, str, str, bool, str, str) # msg, api_url, api_key, save_psd, template_dir, output_dir
    reference_requested = QtCore.pyqtSignal(str, str, str, str, bool, str, str) # ref_path, msg, api_url, api_key, save_psd, template_dir, output_dir
    stop_requested = QtCore.pyqtSignal()  # emitted when user clicks Stop

    def __init__(self, psd_folder, output_folder):
        super().__init__()
        self.setupUi(self)
        self.psd_folder = psd_folder
        self.output_folder = output_folder

        self._reference_image_path = None

        # Connect UI interactions
        self.pushButton_2.clicked.connect(self.browse_template_folder)
        self.pushButton_3.clicked.connect(self.browse_output_folder)
        self.chatSendBtn.clicked.connect(self.on_chat_send)
        self.chatInput.returnPressed.connect(self.on_chat_send)
        self.uploadRefBtn.clicked.connect(self.on_upload_reference)

        self._task_running = False  # track running state

        self.textEdit.setText(self.psd_folder)
        self.textEdit_2.setText(self.output_folder)
        
        self.load_stylesheet()
        self.append_system_msg("Advanced Agentic Composition Engine initialized. Type a prompt to begin!")

    def load_stylesheet(self):
        qss_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "theme.qss")
        if os.path.exists(qss_file):
            with open(qss_file, "r") as file:
                self.setStyleSheet(file.read())

    @QtCore.pyqtSlot(str)
    def append_system_msg(self, msg):
        html = f'<table width="100%" border="0"><tr><td align="center"><span style="color: #8888aa; font-style: italic; font-size: 12px;">[SYSTEM] {msg}</span></td></tr></table>'
        self.chatHistory.append(html)

    @QtCore.pyqtSlot(str)
    def append_agent_msg(self, msg):
        safe_msg = msg.replace('\n', '<br>')
        html = f'''
        <table width="100%" border="0" cellpadding="0" cellspacing="5"><tr><td align="left">
            <table border="0" cellpadding="0" cellspacing="0"><tr>
                <td style="background-color: #2b2d42; color: #ffffff; padding: 12px 18px; border-radius: 15px; border: 1px solid #313246; font-size: 14px; text-align: left;">
                    <b style="color: #ffc107;">🤖 Agent:</b><br><br>{safe_msg}
                </td>
            </tr></table>
        </td></tr></table>
        '''
        self.chatHistory.append(html)

    @QtCore.pyqtSlot(str)
    def append_tool_call(self, msg):
        html = f'''
        <table width="100%" border="0" cellpadding="0" cellspacing="2"><tr><td align="left">
            <table border="0" cellpadding="0" cellspacing="0"><tr>
                <td style="background-color: #1c1e2b; color: #a8b2d1; padding: 8px 15px; border-radius: 8px; border-left: 4px solid #ffc107; font-family: monospace; font-size: 12px; text-align: left;">
                    ⚙️ <b>Tool Call:</b> {msg}
                </td>
            </tr></table>
        </td></tr></table>
        '''
        self.chatHistory.append(html)
        
    @QtCore.pyqtSlot(str)
    def append_user_msg(self, msg):
        safe_msg = msg.replace('\n', '<br>')
        html = f'''
        <table width="100%" border="0" cellpadding="0" cellspacing="5"><tr><td align="right">
            <table border="0" cellpadding="0" cellspacing="0"><tr>
                <td style="background-color: #313246; color: #ffffff; padding: 12px 18px; border-radius: 15px; font-size: 14px; text-align: left;">
                    <b style="color: #ffc107;">👤 You:</b><br><br>{safe_msg}
                </td>
            </tr></table>
        </td></tr></table>
        '''
        self.chatHistory.append(html)

    @QtCore.pyqtSlot(str)
    def update_preview_image(self, image_path):
        if os.path.exists(image_path):
            pixmap = QtGui.QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(self.previewLabel.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.previewLabel.setPixmap(scaled_pixmap)

    @QtCore.pyqtSlot(bool)
    def set_task_running(self, running: bool):
        """Swap the Send button to a Stop button while a task is running."""
        self._task_running = running
        if running:
            # Disconnect Send, connect Stop
            try:
                self.chatSendBtn.clicked.disconnect()
            except:
                pass
            self.chatSendBtn.setText("⏹ Stop")
            self.chatSendBtn.setStyleSheet("""
                QPushButton {
                    background-color: #e63946;
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #ff6b6b;
                }
            """)
            self.chatSendBtn.clicked.connect(self.on_stop_clicked)
            self.chatInput.setEnabled(False)
        else:
            # Reconnect Send
            try:
                self.chatSendBtn.clicked.disconnect()
            except:
                pass
            self.chatSendBtn.setText("Send")
            self.chatSendBtn.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: #0a192f;
                    font-weight: bold;
                    font-size: 14px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #ffd54f;
                }
            """)
            self.chatSendBtn.clicked.connect(self.on_chat_send)
            self.chatInput.setEnabled(True)

    def on_stop_clicked(self):
        """User clicked Stop — request task interruption."""
        self.stop_requested.emit()
        self.chatSendBtn.setText("Stopping...")
        self.chatSendBtn.setEnabled(False)

    def on_upload_reference(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Reference Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            self._reference_image_path = file_path
            self.append_system_msg(f"📎 Reference image loaded: {os.path.basename(file_path)}")
            # Show thumbnail in preview panel
            pixmap = QtGui.QPixmap(file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.previewLabel.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.previewLabel.setPixmap(scaled)
            self.chatInput.setPlaceholderText("Describe what to recreate (or press Send to auto-recreate)...")

    def on_chat_send(self):
        msg = self.chatInput.text().strip()
        api_url = self.baseUrlEdit.text()
        api_key = self.apiKeyEdit.text()
        save_psd = self.checkBox.isChecked()
        template_dir = self.textEdit.text()
        output_dir = self.textEdit_2.text()

        # If a reference image is attached, send via reference signal
        if self._reference_image_path:
            ref_path = self._reference_image_path
            self._reference_image_path = None  # consume it
            self.chatInput.clear()
            self.chatInput.setPlaceholderText("Tell the AI what to design or change...")
            user_note = msg if msg else "Recreate this design as accurately as possible."
            self.append_user_msg(f"📎 [Reference Image] {user_note}")
            self.reference_requested.emit(ref_path, user_note, api_url, api_key, save_psd, template_dir, output_dir)
            return

        if not msg: return
        self.chatInput.clear()
        self.append_user_msg(msg)
        self.chat_requested.emit(msg, api_url, api_key, save_psd, template_dir, output_dir)

    def browse_template_folder(self):
        folder_selected = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Template Folder")
        if folder_selected:
            self.textEdit.setText(folder_selected)
            self.psd_folder = folder_selected

    def browse_output_folder(self):
        folder_selected = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder_selected:
            self.textEdit_2.setText(folder_selected)
            self.output_folder = folder_selected

    def show_save_success_dialog(self, saved_files):
        self.append_system_msg(f"All jobs finished successfully. {len(saved_files)} file(s) saved.")
