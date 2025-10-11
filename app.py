from flask import Flask, request, render_template, abort, jsonify, send_from_directory, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import requests
import base64
import json
import re

# --------------------------------------------------------
# Initialisation
# --------------------------------------------------------
app = Flask(__name__)
app.secret_key = "dev_secret_key"  # ✅ nécessaire pour les flash messages
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@db:5432/myapp"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --------------------------------------------------------
# Modèle Image
# --------------------------------------------------------
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100))
    bio = db.Column(db.Text)

# --------------------------------------------------------
# Upload
# --------------------------------------------------------
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploaded_images'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --------------------------------------------------------
# Routes
# --------------------------------------------------------
@app.route('/')
def accueil():
    return render_template('accueil.html')

@app.route('/import')
def new_personnage():
    return render_template('import.html')

@app.route('/galerie')
def galerie():
    images = Image.query.all()
    return render_template('galerie.html', images=images)

@app.route('/carte/<int:image_id>')
def carte(image_id):
    image = Image.query.get(image_id)
    if not image:
        abort(404)
    return render_template('carte.html', image=image)

@app.route('/uploaded_images/<filename>')
def uploaded_images(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --------------------------------------------------------
# Upload + génération IA
# --------------------------------------------------------
@app.route('/upload_personnage', methods=['POST'])
def upload_personnage():
    debug_content = ""

    if 'image' not in request.files:
        flash("❌ Aucun fichier envoyé", "error")
        return render_template('import.html', debug=debug_content)

    file = request.files['image']
    if file.filename == '':
        flash("❌ Aucun fichier sélectionné", "error")
        return render_template('import.html', debug=debug_content)

    if not allowed_file(file.filename):
        flash("❌ Format de fichier non autorisé", "error")
        return render_template('import.html', debug=debug_content)

    try:
        # Sauvegarde du fichier
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Encode image en base64
        with open(filepath, "rb") as img_file:
            image_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        # Prompt dynamique
        prompt = (
            "Analyse cette image et invente un personnage. "
            "Réponds uniquement en JSON avec ce format :\n"
            '{ "name": "<nom du personnage>", "bio": "<une biographie courte et cohérente>" }'
        )

        OLLAMA_URL = os.getenv("OLLAMA_API_BASE", "http://ai:11434")

        # Requête vers Ollama
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "gemma3:latest",
                "messages": [{"role": "user", "content": prompt, "images": [image_base64]}]
            },
            timeout=180
        )

        debug_content += f"RAW RESPONSE:\n{response.text}\n\n"

        # Fusionner tous les fragments de réponse ligne par ligne
        all_content = ""
        for line in response.text.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            content = obj.get("message", {}).get("content", "")
            all_content += content

        # Nettoyer les ```json et ```
        all_content = re.sub(r"```json|```", "", all_content).strip()

        # Extraire le vrai JSON
        match = re.search(r"\{.*\}", all_content, re.DOTALL)
        if not match:
            flash("⚠️ Impossible de lire la réponse finale de l'IA.", "error")
            return render_template('import.html', debug=all_content)

        ollama_response = json.loads(match.group(0))

        # Sauvegarde dans la base de données
        new_image = Image(
            filename=filename,
            name=ollama_response.get("name"),
            bio=ollama_response.get("bio")
        )
        db.session.add(new_image)
        db.session.commit()

        flash("✅ Personnage généré et sauvegardé !", "success")
        return redirect(url_for('carte', image_id=new_image.id))

    except Exception as e:
        debug_content += f"EXCEPTION:\n{str(e)}\n\n"
        flash(f"❌ Erreur serveur : {str(e)}", "error")
        return render_template('import.html', debug=debug_content)


# --------------------------------------------------------
# Test IA
# --------------------------------------------------------
@app.route('/test_ai')
def test_ai():
    OLLAMA_URL = os.getenv("OLLAMA_API_BASE", "http://ai:11434")
    r = requests.post(f"{OLLAMA_URL}/api/generate", json={"model": "gemma3", "prompt": "Dis bonjour."})
    return r.text

# --------------------------------------------------------
# Lancement
# --------------------------------------------------------
if __name__ == '__main__':
    print("📂 Dossier d'upload :", UPLOAD_FOLDER)
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
