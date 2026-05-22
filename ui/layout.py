# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1200, 800)
        # Enable minimize and close buttons on the title bar
        Dialog.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )

        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")

        self.tabWidget = QtWidgets.QTabWidget(Dialog)
        self.tabWidget.setObjectName("tabWidget")

        # ── Workspace Tab ────────────────────────────────────────────
        self.workspace_tab = QtWidgets.QWidget()
        self.workspace_tab.setObjectName("workspace_tab")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.workspace_tab)
        self.horizontalLayout.setObjectName("horizontalLayout")

        # Left Panel (Chat)
        self.leftPanelLayout = QtWidgets.QVBoxLayout()
        self.leftPanelLayout.setObjectName("leftPanelLayout")

        self.chatHistory = QtWidgets.QTextBrowser(self.workspace_tab)
        self.chatHistory.setObjectName("chatHistory")
        self.chatHistory.setOpenExternalLinks(True)
        self.chatHistory.setStyleSheet(
            "background-color: #1b1c25; color: #ffffff; "
            "border: 1px solid #313246; padding: 10px; font-size: 14px;"
        )
        self.leftPanelLayout.addWidget(self.chatHistory)

        self.chatInputLayout = QtWidgets.QHBoxLayout()
        self.chatInput = QtWidgets.QLineEdit(self.workspace_tab)
        self.chatInput.setObjectName("chatInput")
        self.chatInput.setMinimumHeight(45)
        self.chatInput.setStyleSheet(
            "background-color: #2b2d42; color: #ffffff; "
            "border: 1px solid #313246; padding: 10px; font-size: 14px; border-radius: 5px;"
        )
        self.chatInputLayout.addWidget(self.chatInput)

        self.uploadRefBtn = QtWidgets.QPushButton(self.workspace_tab)
        self.uploadRefBtn.setObjectName("uploadRefBtn")
        self.uploadRefBtn.setMinimumHeight(45)
        self.uploadRefBtn.setMinimumWidth(45)
        self.uploadRefBtn.setMaximumWidth(50)
        self.uploadRefBtn.setToolTip("Upload a reference image for the AI to recreate")
        self.uploadRefBtn.setStyleSheet("""
            QPushButton {
                background-color: #2b2d42;
                color: #ffc107;
                font-size: 18px;
                border: 1px solid #313246;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3b3d52;
                border-color: #ffc107;
            }
        """)
        self.uploadRefBtn.setAutoDefault(False)
        self.uploadRefBtn.setDefault(False)
        self.chatInputLayout.addWidget(self.uploadRefBtn)

        self.chatSendBtn = QtWidgets.QPushButton(self.workspace_tab)
        self.chatSendBtn.setObjectName("chatSendBtn")
        self.chatSendBtn.setMinimumHeight(45)
        self.chatSendBtn.setMinimumWidth(100)
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
        self.chatSendBtn.setAutoDefault(False)
        self.chatSendBtn.setDefault(False)
        self.chatInputLayout.addWidget(self.chatSendBtn)
        self.leftPanelLayout.addLayout(self.chatInputLayout)

        self.horizontalLayout.addLayout(self.leftPanelLayout, stretch=1)

        # Right Panel (Preview)
        self.rightPanelLayout = QtWidgets.QVBoxLayout()
        self.rightPanelLayout.setObjectName("rightPanelLayout")

        self.previewTitleLabel = QtWidgets.QLabel(self.workspace_tab)
        self.previewTitleLabel.setObjectName("previewTitleLabel")
        self.rightPanelLayout.addWidget(self.previewTitleLabel)

        self.previewLabel = QtWidgets.QLabel(self.workspace_tab)
        self.previewLabel.setObjectName("previewLabel")
        self.previewLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.previewLabel.setStyleSheet(
            "background-color: #1b1c25; border: 1px solid #313246;"
        )
        self.previewLabel.setMinimumSize(500, 500)
        self.previewLabel.setScaledContents(False)
        self.rightPanelLayout.addWidget(self.previewLabel, stretch=1)

        self.horizontalLayout.addLayout(self.rightPanelLayout, stretch=1)
        self.tabWidget.addTab(self.workspace_tab, "")

        # ── Settings Tab ─────────────────────────────────────────────
        self.settings_tab = QtWidgets.QWidget()
        self.settings_tab.setObjectName("settings_tab")
        self.settingsLayout = QtWidgets.QVBoxLayout(self.settings_tab)
        self.settingsLayout.setObjectName("settingsLayout")

        # API Settings
        self.apiGroupBox = QtWidgets.QGroupBox(self.settings_tab)
        self.apiGroupBox.setObjectName("apiGroupBox")
        self.formLayout = QtWidgets.QFormLayout(self.apiGroupBox)
        self.formLayout.setObjectName("formLayout")

        self.baseUrlEdit = QtWidgets.QLineEdit(self.apiGroupBox)
        self.baseUrlEdit.setObjectName("baseUrlEdit")
        self.baseUrlEdit.setText("http://localhost:1234/v1")
        self.formLayout.addRow("LM Studio Base URL:", self.baseUrlEdit)

        self.apiKeyEdit = QtWidgets.QLineEdit(self.apiGroupBox)
        self.apiKeyEdit.setObjectName("apiKeyEdit")
        self.apiKeyEdit.setText("sk-lm-OsYvHVHz:G3IQqktjukZA0GMyviOc")
        self.apiKeyEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.formLayout.addRow("API Key:", self.apiKeyEdit)
        self.settingsLayout.addWidget(self.apiGroupBox)

        # Folders Settings
        self.foldersGroupBox = QtWidgets.QGroupBox(self.settings_tab)
        self.foldersGroupBox.setObjectName("foldersGroupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.foldersGroupBox)
        self.gridLayout.setObjectName("gridLayout")

        self.textEdit = QtWidgets.QLineEdit(self.foldersGroupBox)
        self.textEdit.setObjectName("textEdit")
        self.textEdit.setReadOnly(True)
        self.gridLayout.addWidget(self.textEdit, 0, 0, 1, 1)

        self.pushButton_2 = QtWidgets.QPushButton(self.foldersGroupBox)
        self.pushButton_2.setObjectName("pushButton_2")
        self.gridLayout.addWidget(self.pushButton_2, 0, 1, 1, 1)

        self.textEdit_2 = QtWidgets.QLineEdit(self.foldersGroupBox)
        self.textEdit_2.setObjectName("textEdit_2")
        self.textEdit_2.setReadOnly(True)
        self.gridLayout.addWidget(self.textEdit_2, 1, 0, 1, 1)

        self.pushButton_3 = QtWidgets.QPushButton(self.foldersGroupBox)
        self.pushButton_3.setObjectName("pushButton_3")
        self.gridLayout.addWidget(self.pushButton_3, 1, 1, 1, 1)
        self.settingsLayout.addWidget(self.foldersGroupBox)

        # Save Options
        self.saveGroupBox = QtWidgets.QGroupBox(self.settings_tab)
        self.saveGroupBox.setObjectName("saveGroupBox")
        self.vboxLayout = QtWidgets.QVBoxLayout(self.saveGroupBox)
        self.vboxLayout.setObjectName("vboxLayout")

        self.checkBox = QtWidgets.QCheckBox(self.saveGroupBox)
        self.checkBox.setObjectName("checkBox")
        self.checkBox.setChecked(False)
        self.vboxLayout.addWidget(self.checkBox)
        self.settingsLayout.addWidget(self.saveGroupBox)

        self.settingsLayout.addStretch(1)

        self.tabWidget.addTab(self.settings_tab, "")
        self.verticalLayout.addWidget(self.tabWidget)

        self.retranslateUi(Dialog)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Des-ai-n — AI Graphic Designer"))
        self.previewTitleLabel.setText(_translate("Dialog", "Live Design Preview:"))
        self.previewLabel.setText(_translate("Dialog", "No Preview Available"))

        self.chatInput.setPlaceholderText(
            _translate("Dialog", "Tell the AI what to design or change...")
        )
        self.chatSendBtn.setText(_translate("Dialog", "Send"))
        self.uploadRefBtn.setText(_translate("Dialog", "📎"))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.workspace_tab),
            _translate("Dialog", "AI Workspace"),
        )

        self.apiGroupBox.setTitle(_translate("Dialog", "API Configuration"))
        self.foldersGroupBox.setTitle(_translate("Dialog", "Directories"))
        self.pushButton_2.setText(_translate("Dialog", "Browse Templates"))
        self.pushButton_3.setText(_translate("Dialog", "Browse Output"))
        self.saveGroupBox.setTitle(_translate("Dialog", "Save Options"))
        self.checkBox.setText(_translate("Dialog", "Save Source PSD files"))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.settings_tab),
            _translate("Dialog", "Settings"),
        )
