from flask import Flask, jsonify, render_template, request, json
from cipher.caesar import CaesarCipher
from cipher.vigenere import VigenereCipher
 
app = Flask(__name__)
#router routes for home page 
@app.route("/")
def home():
    return render_template('index.html')

#router routes for ceesar cypher
@app.route("/api/caesar/encrypt")
def ceasar():
    return render_template('caesar.html')

@app.route("/api/caesar/encrypt", methods=["POST"])
def caesar_encrypt():
    data = request.json
    plain_text = data['plain_text']
    key = int(data['key'])
    Caesar = CaesarCipher()
    encrypted_text = Caesar.encrypt_text(plain_text, key)
    return jsonify({'encrypted_message': encrypted_text})
@app.route("/api/caesar/decrypt", methods = ["POST"])
def caesar_decrypt():
    data = request.json
    cipher_text = data['cipher_text']
    key = int(data['key'])
    Caesar = CaesarCipher()
    decrypted_text =  Caesar.decrypt_text(cipher_text, key)
    return jsonify({'decrypted_message': decrypted_text})

vigenere_cipher = VigenereCipher()

@app.route('/api/vigenere/encrypt', methods=['POST'])
def vigenere_encrypt():
    data = request.json
    plain_text = data['plain_text']
    key = data['key']
    encrypted_text = vigenere_cipher.vigenere_encrypt(plain_text, key)
    return jsonify({'encrypted_text': encrypted_text})

@app.route('/api/vigenere/decrypt', methods=['POST'])
def vigenere_decrypt():
    data = request.json
    cipher_text = data['cipher_text'] 
    key = data['key']
    decrypted_text = vigenere_cipher.vigenere_decrypt(cipher_text, key)
    return jsonify({'decrypted_text': decrypted_text})


#main function
if __name__ == "__main__":
    app.run(host="0.0.0.0", port = 5000, debug = True)
    