import os
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'study-smart-2026-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///study_planner.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    confidence = db.Column(db.Integer, default=5)  # 1-10 scale
    weightage = db.Column(db.Integer, default=1)   # 1-5 scale (credits/difficulty)
    status = db.Column(db.String(20), default='Pending')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'date': self.exam_date.strftime('%Y-%m-%d'),
            'confidence': self.confidence,
            'weightage': self.weightage
        }

# Core AI Priority Logic
def calculate_priority_engine(subjects, daily_hours=4):
    """
    Advanced Algorithm:
    Score = (Urgency_Factor * Weightage) / (Confidence + 1)
    """
    today = datetime.now().date()
    calculated_plan = []
    
    # Sort by raw urgency first
    sorted_subjects = sorted(subjects, key=lambda x: x.exam_date)
    
    for sub in sorted_subjects:
        days_left = (sub.exam_date - today).days
        if days_left <= 0: days_left = 0.5 # Avoid division by zero
        
        # Urgency: Subjects closer to exam date get higher scores
        urgency = 100 / days_left
        
        # Priority Score
        # We divide by (confidence + 1) because higher confidence should lower priority
        score = (urgency * sub.weightage) / (sub.confidence / 2 + 1)
        
        # Suggested study hours per day for this subject
        suggested_time = (score / 10) * (daily_hours / len(subjects))
        
        calculated_plan.append({
            'name': sub.name,
            'score': round(score, 2),
            'days_left': int(days_left) if days_left >= 1 else 0,
            'suggested_hours': round(min(suggested_time, daily_hours), 1),
            'priority_level': 'High' if score > 50 else 'Medium' if score > 20 else 'Low'
        })
    
    return sorted(calculated_plan, key=lambda x: x['score'], reverse=True)

# Routes
@app.route('/')
def index():
    subjects = Subject.query.order_by(Subject.exam_date).all()
    return render_template('index.html', subjects=subjects)

@app.route('/api/subjects', methods=['POST'])
def add_subject():
    data = request.json
    try:
        new_sub = Subject(
            name=data['name'],
            exam_date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            confidence=int(data['confidence']),
            weightage=int(data['weightage'])
        )
        db.session.add(new_sub)
        db.session.commit()
        return jsonify({"message": "Subject added successfully", "id": new_sub.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/generate-plan', methods=['GET'])
def get_ai_plan():
    subjects = Subject.query.all()
    if not subjects:
        return jsonify([])
    
    # Assume 5 hours of study time per day for calculation
    plan = calculate_priority_engine(subjects, daily_hours=5)
    return jsonify(plan)

@app.route('/api/delete/<int:id>', methods=['DELETE'])
def delete_subject(id):
    sub = Subject.query.get(id)
    if sub:
        db.session.delete(sub)
        db.session.commit()
        return jsonify({"message": "Deleted"})
    return jsonify({"error": "Not found"}), 404

# Database Initializer
def init_db():
    if not os.path.exists('study_planner.db'):
        with app.app_context():
            db.create_all()
            print("Database initialized.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)
