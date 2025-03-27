from flask import Flask, render_template, request, redirect, url_for
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
                check_logged = conn.execute( # query to see if anyone is logged in
                    text('SELECT * FROM users WHERE logged_in = 1') # 1 = True, 0 = False
                    ).fetchone()

                if check_logged: # logs out anyone logged in already
                    conn.execute(
                        text('UPDATE users SET logged_in = 0 WHERE logged_in = 1')
                    )
                    
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
            check_existing = conn.execute(
                text('SELECT * FROM users WHERE username = :username'),
                {'username': username}
            ).fetchone() 
            
            if check_existing: 
                check_password = conn.execute(
                    text('SELECT * FROM users WHERE username = :username AND password = :password'),
                    {'username': username, 'password': password}
                ).fetchone()
                
                if check_password:
                    # Need to change the login status 
                    return render_template('base.html', error='Password is correct')
                else:
                    return render_template('base.html', error='Incorrect login')

            else:
                return render_template('base.html', error='Incorrect login')

    except:
        return render_template('base.html', error='an error occured')


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


@app.route('/test_page', methods=['GET', 'POST'])
def test_page():
    logged_in_user = conn.execute(
        text('SELECT * FROM users WHERE logged_in = 1 LIMIT 1')
    ).fetchone()

    if not logged_in_user:
        return redirect(url_for('index'))

    user_id = logged_in_user[0]  
    user = conn.execute(
        text('SELECT * FROM users WHERE id = :user_id'),
        {'user_id': user_id}
    ).fetchone()

    if not user or user[4] != 'Teacher': 
        return redirect(url_for('index'))

    tests = conn.execute(
        text('SELECT * FROM tests WHERE teacher_id = :teacher_id'),
        {'teacher_id': user_id}
    ).fetchall()

    if request.method == 'POST':
        conn.execute(
            text('INSERT INTO tests (teacher_id) VALUES (:teacher_id)'),
            {'teacher_id': user_id}
        )
        return redirect(url_for('test_page'))

    return render_template('tests.html', tests=tests)


if __name__ == '__main__': 
    app.run(debug = True)