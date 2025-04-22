import sqlite3
import helpers
import hashlib

class Database():
    FILE = ""
    def __init__(self, filename: str):
        self.FILE = filename
        print("db: setupdb - Creating/Updating tables")
        conn, cursor = self.handle()

        # roles table for permission management
        # ID, Name (e.g., 'user', 'moderator', 'admin')
        cursor.execute('''CREATE TABLE IF NOT EXISTS roles (
                    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )''')

        # boards table for categorizing posts
        # ID, Name, Description
        # Note: Simple independent boards. If a hierarchy is needed, add a parent_board_id
        cursor.execute('''CREATE TABLE IF NOT EXISTS boards (
                    board_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT
                )''')

        # users table
        # Added role_id foreign key
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL, -- Should store password hash
                    cookie TEXT UNIQUE, -- For remember me functionality, optional
                    role_id INTEGER DEFAULT 1, -- Default role_id, e.g., 1 for 'user'
                    FOREIGN KEY (role_id) REFERENCES roles (role_id)
                )''')

        # posts table
        # Changed board TEXT to board_id INTEGER FOREIGN KEY
        # Removed Reputation (JSON) and Lastrep
        # Added total_upvotes for quick access
        cursor.execute('''CREATE TABLE IF NOT EXISTS posts (
                    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board_id INTEGER NOT NULL, -- Link to the boards table
                    owner_id INTEGER, -- Link to the users table (can be NULL for anonymous)
                    title TEXT,
                    description TEXT, -- Or content for the main post body
                    image_url TEXT, -- Added field for image URL/path
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL, -- To track last activity
                    FOREIGN KEY (board_id) REFERENCES boards (board_id),
                    FOREIGN KEY (owner_id) REFERENCES users (user_id)
                )''')
                
        # Note: You might want a separate table for post images if multiple images per post are allowed.

        # comments table
        cursor.execute('''CREATE TABLE IF NOT EXISTS comments (
                    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL, -- Link to the posts table
                    owner_id INTEGER, -- Link to the users table (can be NULL for anonymous)
                    parent_comment_id INTEGER, -- Link to parent comment for threading
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL, -- To track last activity
                    FOREIGN KEY (post_id) REFERENCES posts (post_id),
                    FOREIGN KEY (owner_id) REFERENCES users (user_id),
                    FOREIGN KEY (parent_comment_id) REFERENCES comments (comment_id)
                )''')

        # for captchas
        cursor.execute('''CREATE TABLE IF NOT EXISTS captchas (
                    captcha_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    captcha_token TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    wave INTEGER NOT NULL,
                    wave_two_solution TEXT NOT NULL
                )''')


        conn.commit()
        print("db: Tables checked/created successfully.")
        conn.close()

        if self.is_first_setup():
            print("Is first setup? Yes.")
            self.first_setup()

    def is_first_setup(self):
        conn, cursor = self.handle()
        cursor.execute("SELECT COUNT(*) FROM boards;")
        yes = cursor.fetchone()[0] == 0
        conn.close()
        return yes

    def first_setup(self):
        conn, cursor = self.handle()
        
        # Roles
        cursor.execute('INSERT INTO roles (name) VALUES ("member")')
        cursor.execute('INSERT INTO roles (name) VALUES ("moderator")')
        cursor.execute('INSERT INTO roles (name) VALUES ("administator")')

        # Boards
        cursor.execute('INSERT INTO boards (name, description) VALUES ("random", "the default board, discussion about anything")')
        cursor.execute('INSERT INTO boards (name, description) VALUES ("qna", "board for questions and answers only")')

        # Finish
        conn.commit()
        conn.close()
    
    def handle(self):
        """
        Get a handle to the database.
        Returns: Connection Object, Cursor Object
        """
        conn = sqlite3.connect(self.FILE)
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON;')
        return conn, cursor

    def board_id_from_name(self, name):
        conn, cursor = self.handle()
        cursor.execute("SELECT board_id FROM boards WHERE name = ? LIMIT 1", (name,))
        id = cursor.fetchone()[0]
        return id

    def new_post(self, board, title, description, image_url = None, owner = None):
        conn, cursor = self.handle()

        board_id = self.board_id_from_name(board)
        created_at, updated_at = helpers.timestamp(), helpers.timestamp()

        cursor.execute("""INSERT INTO posts (board_id, owner_id, title, description, image_url, created_at, updated_at) 
                                        VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                                        (board_id, owner, title, description, image_url, created_at, updated_at))

        conn.commit()
        conn.close()

    def list_boards(self):
        conn, cursor = self.handle()
        cursor.execute("SELECT name FROM boards ORDER BY board_id ASC")
        boards = [board[0] for board in cursor.fetchall()]
        conn.close()
        return boards # board id 0 first

    def all_newest_posts(self, page = 0, top = 25):
        conn, cursor = self.handle()
        sql = """
            SELECT
                p.post_id,
                p.title,
                p.description,
                p.image_url,
                p.created_at,
                p.updated_at,
                b.name AS board_name,
                u.username AS owner_username
            FROM
                posts p
            JOIN
                boards b ON p.board_id = b.board_id
            LEFT JOIN
                users u ON p.owner_id = u.user_id
            ORDER BY
                p.updated_at DESC
            LIMIT ? OFFSET ?
        """

        posts_list = []

        try:
            cursor.execute(sql, (top, page*top))

            rows = cursor.fetchall()

            for row in rows:
                post_dict = {
                    'post_id': row[0], # p.post_id
                    'title': row[1],   # p.title
                    'description': row[2], # p.description
                    'image_url': row[3], # p.image_url
                    'created_at': helpers.time_ago(row[4]), # p.created_at
                    'updated_at': row[5], # p.updated_at
                    'board': row[6],   # b.name (board_name alias)
                    'owner': row[7] if row[7] is not None else 'Anonymous'
                }
                posts_list.append(post_dict)

        except Exception as e:
            posts_list = [] 
        finally:
            conn.close()

        return posts_list

    def newest_posts(self, board, page = 0, top = 25):
        conn, cursor = self.handle()

        board_id = self.board_id_from_name(board)
        if board_id is None:
            print(f"Info: Board '{board}' not found.")
            conn.close()
            return []
        
        sql = """
            SELECT
                p.post_id,
                p.title,
                p.description,
                p.image_url,
                p.created_at,
                p.updated_at,
                b.name AS board_name,
                u.username AS owner_username
            FROM
                posts p
            JOIN
                boards b ON p.board_id = b.board_id
            LEFT JOIN
                users u ON p.owner_id = u.user_id
            WHERE
                p.board_id = ?
            ORDER BY
                p.updated_at DESC
            LIMIT ? OFFSET ?
        """

        posts_list = []

        try:
            cursor.execute(sql, (board_id, top, page*top))

            rows = cursor.fetchall()

            for row in rows:
                post_dict = {
                    'post_id': row[0], # p.post_id
                    'title': row[1],   # p.title
                    'description': row[2], # p.description
                    'image_url': row[3], # p.image_url
                    'created_at': helpers.time_ago(row[4]), # p.created_at
                    'updated_at': row[5], # p.updated_at
                    'board': row[6],   # b.name (board_name alias)
                    'owner': row[7] if row[7] is not None else 'Anonymous'
                }
                posts_list.append(post_dict)

        except Exception as e:
            posts_list = [] 
        finally:
            conn.close()

        return posts_list
    
    #### CAPTCHA ####

    def captcha_create(self):
        conn, cursor = self.handle()
        wave = 1
        captcha_token = helpers.generate_uuid()
        wave_two_solution = helpers.generate_short_code()
        created_at = helpers.timestamp()

        cursor.execute("INSERT INTO captchas (captcha_token, created_at, wave, wave_two_solution) VALUES (?, ?, ?, ?)",
                        (captcha_token, created_at, wave, wave_two_solution))
        conn.commit()
        conn.close()

        # could be put anywhere but here is a good place i think
        self.captcha_purge()

        return captcha_token
    
    def captcha_delete(self, captcha_token):
        conn, cursor = self.handle()
        cursor.execute("DELETE FROM captchas WHERE captcha_token = ?", (captcha_token,))
        conn.commit()
        conn.close()

    def captcha_purge(self):
        conn, cursor = self.handle()
        created = helpers.timestamp()
        # remove old captchas, solved 10min+ ago
        time_threshold = helpers.timestamp() - 600
        cursor.execute("DELETE FROM captchas WHERE created_at < ?", (time_threshold,))
        conn.commit()
        conn.close()

    def captcha_check_wave_1(self, captcha_token, nonce, difficulty=15):
        conn, cursor = self.handle()
        # check if the challenge is even valid, if not, spoofed solution
        cursor.execute("SELECT COUNT(*) FROM captchas WHERE captcha_token = ?", (captcha_token,))
        count = cursor.fetchone()[0]
        if count == 0: 
            conn.close()
            return False # captcha was never even created
        # captchas already on wave 2 are also invalid
        cursor.execute("SELECT wave FROM captchas WHERE captcha_token = ?", (captcha_token,))
        wave = cursor.fetchone()[0]
        if wave == 2:
            conn.close()
            return False
        # compute hash challenge
        challenge = "popcap-" + captcha_token + "-popcap-" + nonce + "-popcap"
        completed = hashlib.sha256(challenge.encode('utf-8')).hexdigest()
        # validity check
        is_valid = completed.count('0') >= difficulty
        # if valid, mark captcha as wave 2, if not, remove captcha from database
        if is_valid:
            cursor.execute("UPDATE captchas SET wave = 2 WHERE captcha_token = ?", (captcha_token,))
        else:
            self.captcha_delete(captcha_token)
        conn.commit()
        conn.close()
        return is_valid

    def captcha_check_wave_2(self, captcha_token, wave_two_input):
        conn, cursor = self.handle()
        # get the w2 solution from db
        cursor.execute("SELECT wave, wave_two_solution FROM captchas WHERE captcha_token = ?", (captcha_token,))
        result = cursor.fetchone()
        if result is None: return False
        wave, wave_two_solution = result
        # do a check if wave 1 was actually solved
        if wave == 1:
            self.captcha_delete(captcha_token)
            return False # wave 1 was not solved, so captcha is invalid
        # check if solution is correct
        is_valid = wave_two_solution == wave_two_input
        # wether valid or not, captcha is no longer needed
        self.captcha_delete(captcha_token)
        # return state
        return is_valid

    def captcha_get_wave_two_solution(self, captcha_token):
        conn, cursor = self.handle()
        cursor.execute("SELECT wave_two_solution FROM captchas WHERE captcha_token = ?", (captcha_token,))
        wave2_sol = cursor.fetchone()[0]
        conn.close()
        return wave2_sol

    #### ENDOFCAPTCHA ####
    
    def board_description(self, board):
        conn, cursor = self.handle()
        cursor.execute("SELECT description FROM boards WHERE name = ? LIMIT 1", (board,))
        desc = cursor.fetchone()[0]
        conn.close()
        return desc
    
    def get_post_by_id(self, post_id):
        conn, cursor = self.handle()
                
        sql = """
            SELECT
                p.post_id,
                p.title,
                p.description,
                p.image_url,
                p.created_at,
                p.updated_at,
                b.name AS board_name,
                u.username AS owner_username
            FROM
                posts p
            JOIN
                boards b ON p.board_id = b.board_id
            LEFT JOIN
                users u ON p.owner_id = u.user_id
            WHERE
                p.post_id = ?
            LIMIT 1
        """

        cursor.execute(sql, (post_id,))
        row = cursor.fetchone()
        post_dict = {
            'post_id': row[0], # p.post_id
            'title': row[1],   # p.title
            'description': row[2], # p.description
            'image_url': row[3], # p.image_url
            'created_at': helpers.time_ago(row[4]), # p.created_at
            'updated_at': row[5], # p.updated_at
            'board': row[6],   # b.name (board_name alias)
            'owner': row[7] if row[7] is not None else 'Anonymous'
        }
        conn.close()
        return post_dict
    
    def get_comments_by_post_id(self, post_id):
        conn, cursor = self.handle()

        sql = """
            SELECT
                c.comment_id,
                c.post_id,
                c.owner_id,
                c.parent_comment_id,
                c.content,
                c.created_at,
                c.updated_at,
                u.username AS owner_username
            FROM
                comments c
            LEFT JOIN
                users u ON c.owner_id = u.user_id
            WHERE
                c.post_id = ?
            ORDER BY
                c.created_at DESC
        """

        comments_list = []
        try:
            cursor.execute(sql, (post_id,))
            rows = cursor.fetchall()

            for row in rows:
                comment_dict = {
                    'comment_id': row[0],
                    'post_id': row[1],
                    'owner_id': row[2],
                    'parent_comment_id': row[3],
                    'content': row[4],
                    'created_at': helpers.time_ago(row[5]), # Format timestamp
                    'updated_at': row[6],
                    'owner': row[7] if row[7] is not None else 'Anonymous',
                    'replies': [] # Initialize replies list for tree building
                }
                comments_list.append(comment_dict)

        except Exception as e:
            print(f"Error fetching comments: {e}")
            comments_list = []
        finally:
            conn.close()

        return comments_list

    def new_comment(self, post_id, content, owner_id=None, parent_comment_id=None):
        conn, cursor = self.handle()
        created_at, updated_at = helpers.timestamp(), helpers.timestamp()

        try:
            cursor.execute("""INSERT INTO comments (post_id, owner_id, parent_comment_id, content, created_at, updated_at)
                              VALUES (?, ?, ?, ?, ?, ?)""",
                           (post_id, owner_id, parent_comment_id, content, created_at, updated_at))
            cursor.execute("UPDATE posts SET updated_at=? WHERE post_id=?", (updated_at, post_id))
            conn.commit()
            print(f"New comment created for post {post_id}.")
        except Exception as e:
            print(f"Error creating comment: {e}")
            conn.rollback()
        finally:
            conn.close()

    # Helper function to build a threaded comment tree from a flat list
    def build_comment_tree(self, comments_list):
        comment_dict = {c['comment_id']: c for c in comments_list}
        root_comments = []

        for comment in comments_list:
            if comment['parent_comment_id'] is None:
                root_comments.append(comment)
            else:
                parent = comment_dict.get(comment['parent_comment_id'])
                if parent is not None:
                    parent['replies'].append(comment)
                # Handle orphaned replies if parent_comment_id exists but parent doesn't exist in list
                # For this implementation, we'll just ignore them or add them as root if needed,
                # but typically you'd ensure data integrity or handle this case.
                # Appending to root if parent not found:
                # else:
                #     root_comments.append(comment)

        # Optional: Sort replies by creation date
        for comment in comment_dict.values():
            if 'replies' in comment:
                comment['replies'].sort(key=lambda x: x['updated_at']) # Sorting by updated_at as created_at is already formatted

        # Sort root comments by creation date
        root_comments.sort(key=lambda x: x['updated_at'])

        return root_comments