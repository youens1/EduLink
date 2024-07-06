from flask import Flask, render_template, redirect, url_for, request,flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import time

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score
import joblib

app = Flask(__name__)
app.secret_key = 'ton_secret_key'

# Edulink IA
#préparation des données
data = pd.read_csv('StudentsPerformance.csv') 

# Définition de la variable cible
data['success'] = ((data['math score'] + data['reading score'] + data['writing score']) / 3 >= 70).astype(int)

# caractéristiques
categorical_features = ['gender', 'lunch', 'parental level of education', 'race/ethnicity', 'test preparation course']
numerical_features = ['math score', 'reading score', 'writing score']

# Encodage one-hot des variables catégorielles
for feature in categorical_features:
    dummies = pd.get_dummies(data[feature], prefix=feature, drop_first=True)
    data = pd.concat([data, dummies], axis=1)

# Sélection des caractéristiques pour le modèle
X = data.drop(['success'] + categorical_features, axis=1)
y = data['success']

# Division des données et entraînement du modèle
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train_scaled, y_train)

# Sauvegarde du modèle et du scaler
joblib.dump(model, 'model.joblib')
joblib.dump(scaler, 'scaler.joblib')


# Page d'accueil
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Récupération des données du formulaire
        gender = request.form['gender']
        lunch = request.form['lunch']
        education = request.form['education']
        ethnicity = request.form['ethnicity']
        preparation = request.form['preparation']
        math_score = int(request.form['math_score'])
        reading_score = int(request.form['reading_score'])
        writing_score = int(request.form['writing_score'])

        # Préparation des données pour la prédiction
        input_data = pd.DataFrame({
            'gender': [gender],
            'lunch': [lunch],
            'parental level of education': [education],
            'race/ethnicity': [ethnicity],
            'test preparation course': [preparation],
            'math score': [math_score],
            'reading score': [reading_score],
            'writing score': [writing_score]
        })

        # Encodage one-hot
        for feature in categorical_features:
            dummies = pd.get_dummies(input_data[feature], prefix=feature, drop_first=True)
            input_data = pd.concat([input_data, dummies], axis=1)

        input_data = input_data.drop(categorical_features, axis=1)

        # Ajout de colonnes manquantes si nécessaire
        for col in X.columns:
            if col not in input_data.columns:
                input_data[col] = 0

        # Réorganisation des colonnes pour correspondre au modèle
        input_data = input_data.reindex(columns=X.columns, fill_value=0)

        # Chargement du modèle et du scaler
        loaded_model = joblib.load('model.joblib')
        loaded_scaler = joblib.load('scaler.joblib')

        # Prédiction
        input_scaled = loaded_scaler.transform(input_data)
        prediction = loaded_model.predict(input_scaled)[0]
        success = "Réussite probable" if prediction == 1 else "Réussite peu probable"

        return render_template('result.html', success=success)

    return render_template('index.html')

#about
@app.route('/about')
def about():
    return render_template('about.html')
#politique
@app.route('/politique')
def politique():
    return render_template('politique.html')


# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Classe User pour Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password, role, fullname, email, phone, adress):
        self.id = id
        self.username = username
        self.password = password
        self.role = role
        self.fullname = fullname
        self.email= email
        self.phone = phone
        self.adress = adress

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect('edulink.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password, role, fullname, email, phone, adress FROM user WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return User(*user)
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('edulink.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password, role, fullname, email, phone, adress FROM user WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and user[2] == password:
            user_obj = User(*user)
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error=True)
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('add_user'))
    elif current_user.role == 'etudiant':
        return redirect(url_for('courses'))
    elif current_user.role == 'prof':
        return redirect(url_for('add_courses'))
    else:
        return render_template('404.html')
# add user
@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        return render_template('404.html')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        for _ in range(5):  # Essayer 5 fois
            try:
                conn = sqlite3.connect('edulink.db', timeout=10)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO user (username, password, role) VALUES (?, ?, ?)", (username, password, role))
                conn.commit()
                conn.close()
                return redirect(url_for('dashboard'))
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    time.sleep(1)  # Attendre 1 seconde avant de réessayer
                else:
                    raise
    return render_template('add_user.html')
# manage users
@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        return render_template('404.html')
    if current_user.role == 'admin':
        conn = sqlite3.connect('edulink.db', timeout=10)
        cursor = conn.cursor()
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            action = request.form.get('action')

            if action == 'delete':
                try:
                    cursor.execute("DELETE FROM user WHERE user_id = ?", (user_id,))
                    conn.commit()
                    flash('Utilisateur supprimé avec succès.', 'success')
                except sqlite3.Error as e:
                    conn.rollback()
                    flash(f'Erreur lors de la suppression : {str(e)}', 'error')
        
        # Récupérer les étudiants
        cursor.execute("SELECT user_id, username, password FROM user WHERE role = 'etudiant' ORDER BY username")
        students = cursor.fetchall()

        # Récupérer les professeurs
        cursor.execute("SELECT user_id, username, password FROM user WHERE role = 'prof' ORDER BY username")
        professors = cursor.fetchall()   
          
    return render_template('manage_users.html', students=students, professors=professors)

# Route pour afficher le formulaire de contact
@app.route('/contact', methods=['GET'])
def contact():
    return render_template('contact.html')

# Route pour traiter le formulaire de contact
@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    fullname = request.form['fullname']
    email = request.form['email']
    phone = request.form['phone']
    subject = request.form['subject']
    message = request.form['message']
    
    conn = sqlite3.connect('edulink.db')
    conn.execute('INSERT INTO messages (fullname, email, phone, subject, message) VALUES (?, ?, ?, ?, ?)',
                 (fullname, email, phone, subject, message))
    conn.commit()
    conn.close()
    
    return 'Merci pour votre message !'

# messages
@app.route('/messages', methods=['GET', 'POST'])
@login_required
def messages():
    if current_user.role == 'admin':
        conn = sqlite3.connect('edulink.db')
        cursor = conn.cursor()
        if request.method == 'POST':
            messages_id = request.form.get('messages_id')
            action = request.form.get('action')
            print('id',messages_id)
            if action == 'delete':
                try:
                    cursor.execute("DELETE FROM messages WHERE messages_id = ?", (messages_id,))
                    conn.commit()
                    flash('Utilisateur supprimé avec succès.', 'success')
                except sqlite3.Error as e:
                    conn.rollback()
                    flash(f'Erreur lors de la suppression : {str(e)}', 'error')    
        cursor.execute('SELECT * FROM messages ORDER BY messages_id')             
        messages = cursor.fetchall()
        return render_template('messages.html', messages=messages)
    else:
        return redirect(url_for('login'))

#add courses
@app.route('/add_courses', methods=['GET', 'POST'])
@login_required
def add_courses():
    if current_user.role == 'prof':
        if request.method == 'POST':
            course_name = request.form['course_name']
            course_description = request.form['course_description']
            course_url = request.form['course_url']
            
            # Vérifier que les champs nécessaires sont remplis
            if course_name and course_description and course_url:
                conn = sqlite3.connect('edulink.db')
                cursor = conn.cursor()
                cursor.execute('INSERT INTO courses (name, description, url) VALUES (?,?,?)', 
                               (course_name, course_description, course_url))
                conn.commit()
                conn.close()
                
                return redirect(url_for('add_courses', done=True))
            else:
                return render_template('add_courses.html', error=True)

        conn = sqlite3.connect('edulink.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT  courses_id, name, description, url FROM courses')
        courses = cursor.fetchall()
        return render_template('add_courses.html', courses=courses)
    else:
        return redirect(url_for('login'))

#delete courses 
@app.route('/delete_cours', methods=['GET', 'POST'])
def delete_cours():
    if request.method == 'POST':
        cours_id = request.form['cours_id']
        conn = sqlite3.connect('edulink.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM courses WHERE courses_id = ?", (cours_id,))
        conn.commit()
        conn.close()
        flash('Cours supprimé avec succès!', 'success')
        return redirect(url_for('add_courses',))

#courses 
@app.route('/courses', methods=['GET', 'POST'])
@login_required
def courses():
    if current_user.role == 'etudiant':
        conn = sqlite3.connect('edulink.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT  name, description, url FROM courses')
        courses = cursor.fetchall()
        return render_template('courses.html', courses=courses)
    else:
        return redirect(url_for('login'))

#profil    
@app.route('/profil')
@login_required
def profil():
    return render_template('profil.html', user=current_user)

#edit profil
@app.route('/edit_profil', methods=['GET', 'POST'])
@login_required
def edit_profil():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        phone = request.form['phone']
        adress = request.form['adress']
        for _ in range(5):  # Essayer 5 fois
            try:
                conn = sqlite3.connect('edulink.db', timeout=10)
                cursor = conn.cursor()
                cursor.execute("UPDATE user SET fullname = ?, email = ?, phone = ? ,adress = ? WHERE user_id = ?", (fullname, email, phone, adress, current_user.id))
                conn.commit()
                conn.close()
                # Mettre à jour les informations de l'utilisateur courant
                current_user.fullname = fullname
                current_user.email = email
                current_user.phone = phone
                return redirect(url_for('profil'))
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    time.sleep(1)  # Attendre 1 seconde avant de réessayer
                else:
                    raise
    return render_template('edit_profil.html', user=current_user)

# add grade
@app.route('/add_grade', methods=['GET', 'POST'])
@login_required
def add_grade():
    if current_user.role == 'prof':
        conn = sqlite3.connect('edulink.db', timeout=10)
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id, fullname FROM user WHERE role = 'etudiant'")
        students = cursor.fetchall()
        
        cursor.execute("SELECT courses_id, name FROM courses")
        courses = cursor.fetchall()
        
        conn.close()
        
        if request.method == 'POST':
            user_id = request.form['user_id']
            course_id = request.form['course_id']
            grade = request.form['grade']
            
            try:
                conn = sqlite3.connect('edulink.db', timeout=10)
                cursor = conn.cursor()
                # Vérifier si la note existe déjà
                cursor.execute("SELECT note FROM notes WHERE user_id = ? AND courses_id = ?", (user_id, course_id))
                existing_grade = cursor.fetchone()
                
                if existing_grade:
                    # Si la note existe déjà, la mettre à jour
                    cursor.execute("UPDATE notes SET note = ? WHERE user_id = ? AND courses_id = ?", (grade, user_id, course_id))
                else:
                    # Sinon, insérer une nouvelle note
                    cursor.execute("INSERT INTO notes (user_id, courses_id, note) VALUES (?, ?, ?)", (user_id, course_id, grade))
                conn.commit()
                conn.close()
                return redirect(url_for('add_grade'))
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    time.sleep(1)  # Attendre 1 seconde avant de réessayer
                else:
                    raise
    else:
        return redirect(url_for('login'))
    return render_template('add_grade.html', students=students, courses=courses)

@app.route('/view_grades', methods=['GET', 'POST'])
@login_required
def view_grades():
    if current_user.role == 'prof':
        conn = sqlite3.connect('edulink.db')
        cursor = conn.cursor()
        
        # Récupérer la liste des cours
        cursor.execute("SELECT courses_id, name FROM courses")
        courses = cursor.fetchall()
        
        selected_course_id = request.form.get('course_id')
        grades = []
        
        if request.method == 'POST' and selected_course_id:
            # Récupérer les notes pour le cours sélectionné
            query = """
            SELECT user.fullname, courses.name, notes.note
            FROM notes
            JOIN user ON notes.user_id = user.user_id
            JOIN courses ON notes.courses_id = courses.courses_id
            WHERE notes.courses_id = ?
            ORDER BY user.fullname, courses.name
            """
            cursor.execute(query, (selected_course_id,))
            grades = cursor.fetchall()
        
        conn.close()
        
        return render_template('view_grades.html', grades=grades, courses=courses, selected_course_id=selected_course_id)
    else:
        return redirect(url_for('login'))


@app.route('/student_grades')
@login_required
def student_grades():
    if current_user.role == 'etudiant':
        conn = sqlite3.connect('edulink.db')
        cursor = conn.cursor()
        
        # Récupérer les notes de l'étudiant courant
        query = """
        SELECT courses.name, notes.note
        FROM notes
        JOIN courses ON notes.courses_id = courses.courses_id
        WHERE notes.user_id = ?
        ORDER BY courses.name
        """
        cursor.execute(query, (current_user.id,))
        grades = cursor.fetchall()
        
        conn.close()
        
        return render_template('student_grades.html', grades=grades)
    else:
        return redirect(url_for('login'))
    
    
    
#not found
@app.route('/<path:path>')
def notFound(path):
    return render_template('404.html')




# logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
