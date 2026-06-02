


from flask import Flask, render_template, request, json
from cipher.caesar import CaesarCipher
from cipher.vigenere import VigenereCipher
from cipher.railfence import RailFenceCipher
from cipher.playfair import PlayFairCipher
from cipher.transposition import TranspositionCipher
 
app = Flask(__name__)
#router routes for home page 

@app.route("/")
def home():
    return render_template('index.html')

#router routes for caesar cypher
@app.route("/caesar")
def ceasar():
    return render_template('caesar.html')

@app.route("/encrypt", methods=['POST'])
def caesar_encrypt():
    text = request.form['InputPlainText']
    key = int(request.form['InputKeyText'])
    Caesar = CaesarCipher()
    encrypted_text = Caesar.encrypt_text(text, key)
    return render_template('caesar.html', output=encrypted_text)  


@app.route("/decrypt", methods = ['POST'])
def caesar_decrypt():
    text = request.form['InputCipherText']
    key = int(request.form['InputKeyText'])
    Caesar = CaesarCipher()
    decrypted_text =  Caesar.decrypt_text(text, key)
    return render_template('caesar.html', output=decrypted_text)

@app.route("/vigenere")
def vigenere():
    return render_template('vigenere.html')

@app.route("/vigenere/encrypt", methods=['POST'])
def vigenere_encrypt():
    text = request.form['InputPlainText']
    key = request.form['InputKeyText']

    Vigenere = VigenereCipher()
    encrypted_text = new_func(text, key, Vigenere)

    return render_template('vigenere.html', output=encrypted_text)

def new_func(text, key, Vigenere):
    encrypted_text = Vigenere.vigenere_encrypt(text, key)
    return encrypted_text

@app.route("/vigenere/decrypt", methods=['POST'])
def vigenere_decrypt():
    text = request.form['InputCipherText']
    key = request.form['InputKeyText']

    Vigenere = VigenereCipher()
    decrypted_text = Vigenere.vigenere_decrypt(text, key)

    return render_template('vigenere.html', output=decrypted_text)




@app.route("/railfence")
def railfence():
    return render_template('railfence.html')

@app.route("/railfence/encrypt", methods=['POST'])
def railfence_encrypt():
    text = request.form['InputPlainText']
    key = int(request.form['InputKeyText'])
    Railfence = RailFenceCipher()
    encrypted_text = Railfence.rail_fence_encrypt(text, key)
    return render_template('railfence.html', output=encrypted_text)

@app.route("/railfence/decrypt", methods=['POST'])
def railfence_decrypt():
    text = request.form['InputCipherText']
    key = int(request.form['InputKeyText'])
    Railfence = RailFenceCipher()
    decrypted_text = Railfence.rail_fence_decrypt(text, key)
    return render_template('railfence.html', output=decrypted_text)

@app.route("/playfair")
def playfair():
    return render_template('playfair.html')

@app.route("/playfair/encrypt", methods=['POST'])
def playfair_encrypt():
    text = request.form['InputPlainText']
    key = request.form['InputKeyText']
    Playfair = PlayFairCipher()
    matrix = Playfair.create_playfair_matrix(key)
    encrypted_text = Playfair.playfair_encrypt(text, matrix)
    return render_template('playfair.html', output=encrypted_text)

@app.route("/playfair/decrypt", methods=['POST'])
def playfair_decrypt():
    text = request.form['InputCipherText']
    key = request.form['InputKeyText']
    Playfair = PlayFairCipher()
    matrix = Playfair.create_playfair_matrix(key)
    decrypted_text = Playfair.playfair_decrypt(text, matrix)
    return render_template('playfair.html', output=decrypted_text)

@app.route("/transposition")
def transposition():
    return render_template('transposition.html')

@app.route("/transposition/encrypt", methods=['POST'])
def transposition_encrypt():
    text = request.form['InputPlainText']
    key = int(request.form['InputKeyText'])
    Transposition = TranspositionCipher()
    encrypted_text = Transposition.encrypt(text, key)
    return render_template('transposition.html', output=encrypted_text)

@app.route("/transposition/decrypt", methods=['POST'])
def transposition_decrypt():
    text = request.form['InputCipherText']
    key = int(request.form['InputKeyText'])
    Transposition = TranspositionCipher()
    decrypted_text = Transposition.decrypt(text, key)
    return render_template('transposition.html', output=decrypted_text)

#main function
if __name__ == "__main__":
    app.run(host="0.0.0.0", port = 5050, debug = True)
