from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import re
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = '12345'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=400)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
db = SQLAlchemy(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    priority = db.Column(db.Integer, nullable=False, default=0)  # 0 = Low, 1 = Medium, 2 = High
    due_date = db.Column(db.DateTime)
    completed = db.Column(db.Boolean, default=False)  # New column for task completion status

    def __repr__(self):
        return '<Task %r>' % self.title



@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Missing username or password"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Missing username or password"}), 400

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({"message": "Invalid username or password"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token), 200

@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({"message": "Successfully logged out"}), 200

@app.route('/api/tasks', methods=['POST'])
@jwt_required()
def create_task():
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    priority = data.get('priority')
    due_date_str = data.get('due_date')
    completed = data.get('completed')

    if not title:
        return jsonify({"message": "Task title is required"}), 400

    # Convert due_date string to datetime object
    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return jsonify({"message": "Invalid due date format. Use format YYYY-MM-DD HH:MM:SS"}), 400

    user_id = get_jwt_identity()
    new_task = Task(user_id=user_id, title=title, description=description, priority=priority, due_date=due_date, completed=completed)
    db.session.add(new_task)
    db.session.commit()

    return jsonify({"message": "Task created successfully"}), 201



@app.route('/api/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    user_id = get_jwt_identity()
    tasks = Task.query.filter_by(user_id=user_id).all()
    return jsonify(tasks=[serialize_task(task) for task in tasks]), 200

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404

    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    priority = data.get('priority')
    due_date = data.get('due_date')

    if title:
        task.title = title
    if description:
        task.description = description
    if priority is not None:
        task.priority = priority
    if due_date:
        # Convert due_date to string if it's not already
        due_date_str = str(due_date)

        # Validate due_date format using regular expression
        if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', due_date_str):
            return jsonify({"message": "Invalid due date format. Use format YYYY-MM-DD HH:MM:SS"}), 400
        task.due_date = due_date

    db.session.commit()
    return jsonify({"message": "Task updated successfully"}), 200

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted successfully"}), 200

# Helper method to serialize task object
def serialize_task(task):
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "due_date": task.due_date.strftime("%Y-%m-%d %H:%M:%S") if task.due_date else None,
        "completed": task.completed
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

