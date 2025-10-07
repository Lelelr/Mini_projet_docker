from flask import Flask, request, render_template
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy

# test
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@db:5432/myapp"
    )
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Image(db.Model):
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)


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
    images = Image.query.all()
    return render_template('galerie.html', images=images)


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
            new_image = Image(filename=filename, filepath=filepath)
            db.session.add(new_image)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            return f"Erreur lors de la sauvegarde du fichier : {e}", 500
        
        return f"Image '{filename}' ajouté avec succès !"
    else:
        return "Format de fichier non autorisé", 400

if __name__ == '__main__':
    print("Dossier d'upload :", UPLOAD_FOLDER)
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)




