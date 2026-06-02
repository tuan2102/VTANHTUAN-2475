import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from ui.caesar import Ui_MainWindow
import requests
import json
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.btnen.clicked.connect(self.call_api_encrypt)
        self.ui.btnde.clicked.connect(self.call_api_decrypt)
        
    def call_api_encrypt(self):
        url = "http://127.0.0.1:5000/api/caesar/encrypt"
        payload = {
            "plain_text": self.ui.txtplaintext.toPlainText(),
            "key": self.ui.txtkey.toPlainText()
        }
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.text
                if isinstance(data, str):
                    # Handle the case when data is a string
                    # For example, if data is the response content from an API
                    # You might need to parse it as JSON
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        # Handle the case when data is not JSON
                        # You might want to show an error message or handle it in some other way
                        pass
                self.ui.txtcptext.setPlainText(data["encrypted_message"])
                
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText("Encrypted Successfully")
                msg.exec_()
            else:
                print("Error while calling API")
        except requests.exceptions.RequestException as e:
            print("Error: %s" %e.message)
    
    def call_api_decrypt(self):
        url = "http://127.0.0.1:5000/api/caesar/decrypt"
        payload = {
            "cipher_text": self.ui.txtcptext.toPlainText(),
            "key": self.ui.txtkey.toPlainText()
        }
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.text
                if isinstance(data, str):
                    # Handle the case when data is a string
                    # For example, if data is the response content from an API
                    # You might need to parse it as JSON
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        # Handle the case when data is not JSON
                        # You might want to show an error message or handle it in some other way
                        pass
                self.ui.txtplaintext.setPlainText(data["decrypted_message"])
                
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText("Decrypted Successfully")
                msg.exec_()
            else:
                print("Error while calling API")
        except requests.exceptions.RequestException as e:
            print("Error: %s" % e.message)
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())