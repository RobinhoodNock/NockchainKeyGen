import sys
import os
import subprocess
import re
import shutil
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QTextEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal

# -----------------------
# Worker to run commands
# -----------------------
class CommandWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, str)

    def __init__(self, command, cwd=None):
        super().__init__()
        self.command = command
        self.cwd = cwd

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd
            )
            ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
            for line in process.stdout:
                clean_line = ansi_escape.sub('', line).strip()
                if clean_line:
                    self.log_signal.emit(clean_line)
            process.wait()
            self.finished_signal.emit(process.returncode, "")
        except Exception as e:
            self.log_signal.emit(f"[ERROR] {str(e)}")
            self.finished_signal.emit(-1, str(e))

# -----------------------
# Main GUI
# -----------------------
class WalletGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robinhoods Nockchain Keygen")
        self.resize(700, 450)

        # Layout
        self.layout = QVBoxLayout()
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.layout.addWidget(self.output)

        self.btn_generate = QPushButton("Generate Key")
        self.btn_generate.clicked.connect(self.generate_keys)
        self.layout.addWidget(self.btn_generate)

        self.btn_export = QPushButton("Save Wallet Keys")
        self.btn_export.clicked.connect(self.save_keys)
        self.layout.addWidget(self.btn_export)

        self.setLayout(self.layout)

        # Check for nockchain-wallet
        self.wallet_command = shutil.which("nockchain-wallet")
        if not self.wallet_command:
            QMessageBox.critical(
                self,
                "Error",
                "nockchain-wallet command not found in PATH.\n"
                "Please install Nockchain and make sure nockchain-wallet is available."
            )
            sys.exit(1)

        self.home = os.path.expanduser("~")

    # -----------------------
    # Append log output
    # -----------------------
    def append_log(self, text):
        self.output.append(text)
        self.output.verticalScrollBar().setValue(
            self.output.verticalScrollBar().maximum()
        )

    # -----------------------
    # Generate keys
    # -----------------------
    def generate_keys(self):
        self.append_log("Generating keys...")
        self.btn_generate.setEnabled(False)
        self.keygen_worker = CommandWorker([self.wallet_command, "keygen"])
        self.keygen_worker.log_signal.connect(self.append_log)
        self.keygen_worker.finished_signal.connect(self.keygen_finished)
        self.keygen_worker.start()

    def keygen_finished(self, returncode, _):
        self.btn_generate.setEnabled(True)
        if returncode == 0:
            self.append_log("[INFO] Key generation completed.")
        else:
            self.append_log("[ERROR] Key generation failed.")

    # -----------------------
    # Save keys
    # -----------------------
    def save_keys(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Wallet Keys",
            os.path.join(self.home, "keys.export"),
            "Export Files (*.export);;All Files (*)"
        )
        if filename:
            QMessageBox.information(
                self,
                "Saving Keys",
                "Saving wallet keys. Please do NOT close the application until it completes."
            )
            self.btn_export.setEnabled(False)
            self.export_worker = CommandWorker([self.wallet_command, "export-keys"])
            self.export_worker.log_signal.connect(self.append_log)
            self.export_worker.finished_signal.connect(lambda rc, _: self.export_finished(rc, filename))
            self.export_worker.start()

    def export_finished(self, returncode, filename):
        self.btn_export.setEnabled(True)
        if returncode == 0:
            try:
                # Run the command again to capture output for file
                process = subprocess.run(
                    [self.wallet_command, "export-keys"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                with open(filename, "w") as f:
                    f.write(process.stdout)
                self.append_log(f"[INFO] Keys saved to {filename}")
                QMessageBox.information(self, "Saved", f"Wallet keys saved to:\n{filename}")
            except Exception as e:
                self.append_log(f"[ERROR] Failed to save keys: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to save keys:\n{str(e)}")
        else:
            self.append_log("[ERROR] Export failed.")

# -----------------------
# Main entry point
# -----------------------
if __name__ == "__main__":
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("PyQt6 not found. Please run: pip install pyqt6")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = WalletGUI()
    window.show()
    sys.exit(app.exec())
