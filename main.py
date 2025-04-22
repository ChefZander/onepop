from flask import Flask, render_template, request, url_for, redirect, Response
import sqlite3
from database import Database
import helpers

database = Database("onepop.db")

app = Flask("onepop")

@app.get('/')
def index():
    posts = database.all_newest_posts(page=int(request.args.get("page", 0)))
    username = database.get_name_from_cookie(request.cookies.get("account"))
    return render_template("index.html", boards=database.list_boards(), recent_posts=posts, current_page=int(request.args.get("page", 0)), username = username)

@app.get('/board/<current_board>')
def index_board(current_board):
    posts = database.newest_posts(current_board, page=int(request.args.get("page", 0)))
    board_description = database.board_description(current_board)
    username = database.get_name_from_cookie(request.cookies.get("account"))
    return render_template("index.html", boards=database.list_boards(), current_board=current_board, recent_posts=posts,
                           board_description=board_description, current_page=int(request.args.get("page", 0)), username = username)

@app.get('/post/<int:post_id>')
def view_post(post_id):
    post_obj = database.get_post_by_id(post_id)
    if post_obj:
        # Get the comment ID to which the user is replying from the query parameters
        replying_to_comment_id = request.args.get('reply_to')
        replying_to_comment = None

        comments_list = database.get_comments_by_post_id(post_id)
        comment_tree = database.build_comment_tree(comments_list)

        username = database.get_name_from_cookie(request.cookies.get("account"))

        # If a reply_to ID is provided, find the corresponding comment object
        if replying_to_comment_id:
            try:
                replying_to_comment_id = int(replying_to_comment_id)
                # Find the comment object in the flat list (or fetched specifically)
                # Fetching it again is simpler here, but could be optimized
                conn, cursor = database.handle()
                cursor.execute("""
                    SELECT
                        c.comment_id, c.post_id, c.owner_id, c.parent_comment_id, c.content, c.created_at, c.updated_at, u.username AS owner_username
                    FROM
                        comments c
                    LEFT JOIN
                        users u ON c.owner_id = u.user_id
                    WHERE
                        c.comment_id = ? AND c.post_id = ?
                    LIMIT 1
                """, (replying_to_comment_id, post_id))
                row = cursor.fetchone()
                conn.close()

                if row:
                     replying_to_comment = {
                        'comment_id': row[0],
                        'post_id': row[1],
                        'owner_id': row[2],
                        'parent_comment_id': row[3],
                        'content': row[4],
                        'created_at': helpers.time_ago(row[5]),
                        'updated_at': row[6],
                        'owner': row[7] if row[7] is not None else 'Anonymous'
                    }
                else:
                    # Invalid reply_to ID for this post, ignore it
                    replying_to_comment_id = None

            except (ValueError, TypeError):
                # Handle cases where reply_to is not a valid integer
                 replying_to_comment_id = None


        return render_template(
            "post.html",
            post=post_obj,
            comments=comment_tree,
            replying_to_comment_id=replying_to_comment_id, # Pass the ID
            replying_to_comment=replying_to_comment, # Pass the comment object for display
            post_id=post_id, boards=database.list_boards(),
            username = username
        )
    else:
        return render_template("post.html", 
                               boards=database.list_boards(), 
                               post=None, comments=[], 
                               replying_to_comment_id=None, 
                               replying_to_comment=None, 
                               post_id=post_id, 
                               username = username)

@app.post('/create_post')
def create_post():
    owner = database.get_id_from_cookie(request.cookies.get("account"))
    image_url = None
    board = request.form.get("board")[:32]
    title = request.form.get("title")[:128]
    description = request.form.get("description")[:4096]

    # check captcha
    captcha_solution = request.form.get("captcha_input")[:10]
    captcha_token = request.form.get("captcha_token")
    is_valid = database.captcha_check_wave_2(captcha_token, captcha_solution)
    if not is_valid:
        return "Invalid captcha."

    # throw out nonsense
    if board not in database.list_boards(): return ""
    if not board.strip(): return ""
    if not title.strip(): return ""
    if not description.strip(): return ""

    database.new_post(board, title, description, image_url=image_url, owner=owner)

    return redirect("/board/" + board)

@app.post('/create_comment')
def create_comment_route():
    post_id = request.form.get('post_id')
    content = request.form.get('content')
    parent_comment_id = request.form.get('parent_comment_id')

    if not post_id or not content:
        return "Missing form data", 400

    # check captcha
    captcha_solution = request.form.get("captcha_input")[:10]
    captcha_token = request.form.get("captcha_token")
    is_valid = database.captcha_check_wave_2(captcha_token, captcha_solution)
    if not is_valid:
        return "Invalid captcha."

    # Get user ID from session/cookie if logged in, otherwise owner_id will be None (anonymous)
    owner_id = database.get_id_from_cookie(request.cookies.get("account"))

    try:
        post_id = int(post_id)
        if parent_comment_id:
            parent_comment_id = int(parent_comment_id)
        else:
            parent_comment_id = None
    except ValueError:
        return "Invalid post_id or parent_comment_id", 400
    # Create the comment in the database
    database.new_comment(post_id, content, owner_id, parent_comment_id)
    return redirect(url_for('view_post', post_id=post_id))

@app.get('/popcap/wave1')
def captcha_w1():
    captcha_token = database.captcha_create()
    return captcha_token
@app.get('/popcap/wave2')
def captcha_w2():
    captcha_token = request.args.get("challenge_token")
    wave1_solution = request.args.get("nonce")
    is_valid = database.captcha_check_wave_1(captcha_token, wave1_solution)
    print(f"popcap: Wave 1 Submitted. tk={captcha_token} n={wave1_solution} v={is_valid}")
    if not is_valid:
        return "Invalid captcha."
    wave2_challenge = database.captcha_get_wave_two_solution(captcha_token)
    wave2_image = helpers.create_captcha_image(wave2_challenge)
    response = Response(response=wave2_image, content_type="image/png")
    return response

@app.get('/login')
def login():
    return render_template("login.html")

@app.post('/login')
def handle_login():
    username = request.form.get("username")
    password = helpers.hash(request.form.get("password"))

    # check captcha
    captcha_solution = request.form.get("captcha_input")[:10]
    captcha_token = request.form.get("captcha_token")
    is_valid = database.captcha_check_wave_2(captcha_token, captcha_solution)
    if not is_valid:
        return "Invalid captcha."

    cookie = database.account_login(username, password)
    if not cookie:
        return "Invalid username or password."
    
    response = redirect("/")
    response.set_cookie("account", cookie)
    return response

@app.get('/signup')
def signup():
    return render_template("signup.html")
@app.post('/signup')
def handle_signup():
    username = request.form.get("username")
    password = helpers.hash(request.form.get("password"))

    # check captcha
    captcha_solution = request.form.get("captcha_input")[:10]
    captcha_token = request.form.get("captcha_token")
    is_valid = database.captcha_check_wave_2(captcha_token, captcha_solution)
    if not is_valid:
        return "Invalid captcha."

    if database.account_exists(username):
        return "Username already exists."

    cookie = database.new_account(username, password)

    response = redirect("/")
    response.set_cookie("account", cookie)
    return response

@app.get('/logout')
def logout():
    response = redirect("/")
    response.delete_cookie("account")
    return response
    

app.run("0.0.0.0", port=8080)