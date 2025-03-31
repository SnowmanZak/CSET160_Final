from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, text

app = Flask(__name__)

conn_str = "mysql://root:cset155@localhost/testmgm"
engine = create_engine(conn_str, echo = True)
conn = engine.connect()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods = ['GET'])
def get_sign_up():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def sign_up():
    name = request.form.get('name')
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    try:
        with engine.begin() as conn: # with connects to the database and ensures it is properly close, begin starts the transactions and commits it
            check_existing = conn.execute(
                text('SELECT * FROM users WHERE username = :username'),
                {'username': username}
            ).fetchone() # fetchone checks to see if any rows are returned
            if check_existing: # if check existing is not none
                return render_template('signup.html', error="Username is already in use.")
            else:
                log_other_users_out(conn)
                    
                conn.execute(
                    text('INSERT INTO users (name, username, password, role, logged_in) VALUES (:name, :username, :password, :role, :logged_in)'),
                    {'name': name, 'username': username, 'password': password, 'role': role, 'logged_in': True}
                )
                return render_template('index.html')
            
    except:
        return render_template('signup.html')

@app.route('/login-submit', methods=['POST'])
def login_submit():
    username = request.form.get('username')
    password = request.form.get('password')
    
    try:
        with engine.begin() as conn:
            check_existing = conn.execute( # Checks to make sure the username exists in DB
                text('SELECT * FROM users WHERE username = :username'),
                {'username': username}
            ).fetchone() 
            
            if check_existing: 
                check_password = conn.execute( # Checks to make sure the password matches the provided username
                    text('SELECT * FROM users WHERE username = :username AND password = :password'),
                    {'username': username, 'password': password}
                ).fetchone()
                
                if check_password:
                    log_other_users_out(conn)

                    conn.execute( # Sets the specific users login to 1 (True)
                        text('UPDATE users SET logged_in = 1 WHERE username = :username AND password = :password'),
                        {'username': username, 'password': password}
                    ) 
            
                    return render_template('base.html')                    
                else:
                    return render_template('base.html', error='Incorrect login')

            else:
                return render_template('base.html', error='Incorrect login')

    except:
        return render_template('base.html', error='an error occured')

@app.route('/log-out', methods=['POST'])
def log_out():
    try:
        with engine.begin() as conn:
          conn.execute(
              text('UPDATE users SET logged_in = 0 WHERE logged_in = 1')
          )  
          
        return render_template('base.html')
    except:
        return render_template('base.html')

# Functions for account logic 
def log_other_users_out(connect):
    check_logged = connect.execute( # query to see if anyone is logged in
        text('SELECT * FROM users WHERE logged_in = 1') # 1 = True, 0 = False
    ).fetchone()

    if check_logged: # logs out anyone logged in already
        connect.execute(
            text('UPDATE users SET logged_in = 0 WHERE logged_in = 1')
        )



@app.route('/accounts', methods = ['GET'])
def accounts():
    role_filter = request.args.get('role', 'all')  

    if role_filter == "all":
        query = text("SELECT * FROM users")
        result = conn.execute(query).fetchall()
    else:
        query = text("SELECT * FROM users WHERE role = :role")
        result = conn.execute(query, {"role": role_filter}).fetchall()
    
    return render_template('accounts.html', accounts=result, selected_role=role_filter)




def get_logged_in_user():
    with engine.connect() as conn:
        user = conn.execute(text("SELECT * FROM Users WHERE logged_in = 1 LIMIT 1")).mappings().first()
    return user

@app.route('/test_page', methods=['GET', 'POST'])
def test_page():
    user = get_logged_in_user()

    if not user:
        return redirect(url_for('index'))  

    if user['role'] == 'Teacher':
        if request.method == 'POST':
            with engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO Tests (teacher_id) VALUES (:teacher_id)"),
                    {'teacher_id': user['user_id']}
                )
                new_test_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                conn.commit()

            return redirect(url_for('create_test', test_id=new_test_id))

        with engine.connect() as conn:
            tests = conn.execute(text("SELECT * FROM Tests WHERE teacher_id = :teacher_id"), {'teacher_id': user['user_id']}).mappings().all()

        return render_template('tests.html', tests=tests, user=user)

    elif user['role'] == 'Student':
        with engine.connect() as conn:
            tests = conn.execute(text("SELECT * FROM Tests")).mappings().all()

        return render_template('tests.html', tests=tests, user=user)

    return redirect(url_for('index'))



@app.route('/create_test/<int:test_id>', methods=['GET', 'POST'])
def create_test(test_id):
    user = get_logged_in_user()
    if not user or user['role'] != 'Teacher':
        return redirect(url_for('index'))

    with engine.connect() as conn:
        if request.method == 'POST':
            question_text = request.form.get('question_text', '').strip()
            if not question_text:
                return render_template('create_test.html', test_id=test_id, error_message="Question text cannot be empty.")
            else:
                conn.execute(
                    text("INSERT INTO Questions (test_id, question_text) VALUES (:test_id, :question_text)"),
                    {'test_id': test_id, 'question_text': question_text}
                )
                conn.commit()

            return redirect(url_for('create_test', test_id=test_id))

        test = conn.execute(text("SELECT * FROM Tests WHERE test_id = :test_id"), {'test_id': test_id}).mappings().first()
        questions = conn.execute(text("SELECT * FROM Questions WHERE test_id = :test_id"), {'test_id': test_id}).mappings().all()

    return render_template('create_test.html', test=test, questions=questions)

@app.route('/delete_test/<int:test_id>', methods=['POST'])
def delete_test(test_id):
    user = get_logged_in_user()
    if not user or user['role'] != 'Teacher':
        return redirect(url_for('index'))

    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM Tests WHERE test_id = :test_id AND teacher_id = :teacher_id"),
            {'test_id': test_id, 'teacher_id': user['user_id']}
        )
        conn.commit()

    return redirect(url_for('test_page'))

@app.route('/finish_test/<int:test_id>', methods=['POST'])
def finish_test(test_id):
    return redirect(url_for('test_page'))

@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    user = get_logged_in_user()  

    if not user or user['role'] != 'Teacher':  
        return redirect(url_for('index'))

    with engine.connect() as conn:
        question = conn.execute(
            text('SELECT * FROM Questions WHERE question_id = :question_id'),
            {'question_id': question_id}
        ).fetchone()

        if not question:
            return redirect(url_for('test_page'))

        if request.method == 'POST':
            new_question_text = request.form.get('question_text', '').strip() 

            if new_question_text:
                conn.execute(
                    text('UPDATE Questions SET question_text = :question_text WHERE question_id = :question_id'),
                    {'question_text': new_question_text, 'question_id': question_id}
                )
                conn.commit()

                return redirect(url_for('create_test', test_id=question[1], message="Question updated successfully!"))
            else:
                return render_template('edit_question.html', question=question, message="Question text cannot be empty.")

    return render_template('edit_question.html', question=question)




@app.route('/take_test/<int:test_id>', methods=['GET', 'POST'])
def take_test(test_id):
    user = get_logged_in_user()

    if not user or user['role'] != 'Student':
        return redirect(url_for('index'))

    with engine.connect() as conn:
        # Check if the student has already taken the test
        existing_response = conn.execute(
            text("SELECT 1 FROM Responses WHERE student_id = :student_id AND test_id = :test_id"),
            {'student_id': user['user_id'], 'test_id': test_id}
        ).fetchone()

        if existing_response:
            return redirect(url_for('test_page', message="You have already taken this test."))

        # Fetch questions for the test
        questions = conn.execute(
            text("SELECT * FROM Questions WHERE test_id = :test_id"),
            {'test_id': test_id}
        ).fetchall()

        # Fetch the test details (e.g., test name, description)
        test = conn.execute(
            text("SELECT * FROM Tests WHERE test_id = :test_id"),
            {'test_id': test_id}
        ).fetchone()

    return render_template('take_test.html', test=test, questions=questions, user=user)



@app.route('/submit_test/<int:test_id>', methods=['POST'])
def submit_test(test_id):
    user = get_logged_in_user()

    if not user or user['role'] != 'Student':  
        return redirect(url_for('index'))

    with engine.connect() as conn:
        test = conn.execute(
            text("SELECT * FROM Tests WHERE test_id = :test_id"),
            {'test_id': test_id}
        ).mappings().first()

        if not test:
            return redirect(url_for('test_page'))

        questions = conn.execute(
            text("SELECT * FROM Questions WHERE test_id = :test_id"),
            {'test_id': test_id}
        ).mappings().all()

        for question in questions:
            answer_text = request.form.get(f'answer_{question['question_id']}', '').strip()

            existing_response = conn.execute(
                text("""
                    SELECT * FROM Responses 
                    WHERE student_id = :student_id 
                    AND test_id = :test_id 
                    AND question_id = :question_id
                """),
                {
                    'student_id': user['user_id'],
                    'test_id': test_id,
                    'question_id': question['question_id']
                }
            ).mappings().first()

            if existing_response:
                conn.execute(
                    text("""
                        UPDATE Responses 
                        SET answer_text = :answer_text 
                        WHERE student_id = :student_id 
                        AND test_id = :test_id 
                        AND question_id = :question_id
                    """),
                    {
                        'answer_text': answer_text,
                        'student_id': user['user_id'],
                        'test_id': test_id,
                        'question_id': question['question_id']
                    }
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO Responses (student_id, test_id, question_id, answer_text) 
                        VALUES (:student_id, :test_id, :question_id, :answer_text)
                    """),
                    {
                        'student_id': user['user_id'],
                        'test_id': test_id,
                        'question_id': question['question_id'],
                        'answer_text': answer_text
                    }
                )

        conn.commit()

    return redirect(url_for('test_page')) 

@app.route('/grade', methods=['GET', 'POST'])
def test_grade():
    user = get_logged_in_user()
    
    if user['role'] == 'Teacher':
        with engine.connect() as conn:
            tests = conn.execute(
                text('SELECT * FROM Tests WHERE teacher_id = :teacher_id'),
                {'teacher_id': user['user_id']}
            ).mappings().all()
              
        return render_template('grades.html', tests=tests, user=user)  
    
    elif user['role'] == 'Student':
        with engine.connect() as conn:
            student_grade = conn.execute(
                text('SELECT * FROM grades WHERE student_id = :student_id'),
                {'student_id': user['user_id']}
            ).mappings().all()
            
        return render_template('grades.html', student_grade=student_grade)
    
    elif not user:
        return render_template('grades.html', test='You must log in')
    
    else:
        return render_template('grades.html', test='An error occured')
                

@app.route('/give-grade', methods=['GET', 'POST'])
def give_grade():
    user = get_logged_in_user()
    test_id = request.args.get('test_id')  
    
    with engine.connect() as conn:
        responses = conn.execute(
            text('SELECT * FROM responses WHERE test_id = :test_id ORDER BY student_id'),
            {'test_id': test_id, 'student_id': user['user_id']}
        ).mappings().all()
        
        
        return render_template('give_grades.html', responses=responses)
    




if __name__ == '__main__': 
    app.run(debug = True)