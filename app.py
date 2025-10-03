from flask import Flask, request, render_template
import os
from werkzeug.utils import secure_filename

# test
app = Flask(__name__)

UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../static/uploaded_images'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 Mo max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def accueil():
    return render_template('accueil.html')

@app.route('/import')
def new_personnage():
    return render_template('import.html')

@app.route('/carte')
def carte():
    return render_template('carte.html')

@app.route('/galerie')
def galerie():
    return render_template('galerie.html')

@app.route('/upload_personnage', methods=['POST'])
def upload_personnage():
    if 'image' not in request.files:
        return "Aucun fichier envoyé", 400

    file = request.files['image']
    if file.filename == '':
        return "Aucun fichier sélectionné", 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
        except Exception as e:
            return f"Erreur lors de la sauvegarde du fichier : {e}", 500
        return f"Personnage '{request.form['nom']}' ajouté avec succès !"
    else:
        return "Format de fichier non autorisé", 400

if __name__ == '__main__':
    print("Dossier d'upload :", UPLOAD_FOLDER)
    app.run(debug=True, host='0.0.0.0', port=5000)
