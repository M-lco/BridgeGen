from flask import jsonify, request
import secrets
import sqlite3
from datetime import datetime
from database import get_db


def dict_from_row(row):
    if row is None:
        return None
    return dict(zip(row.keys(), row))


def format_time_ago(created_at):
    if isinstance(created_at, str):
        try:
            created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        except:
            return created_at
    
    now = datetime.now()
    diff = now - created_at
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f'{mins}m ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours}h ago'
    else:
        days = int(seconds / 86400)
        return f'{days}d ago'


def register_routes(app):
    
    @app.route('/api/posts', methods=['GET'])
    def get_posts():
        user_id = request.args.get('userId', 'user-matt')
        word_id = request.args.get('wordId', type=int)
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            if word_id:
                cursor.execute("""
                    SELECT p.id, p.user_id as userId, p.text, p.likes_count as likes, 
                           p.created_at, p.word_id,
                           u.name as author, u.initials, u.age, u.type
                    FROM posts p
                    JOIN users u ON p.user_id = u.id
                    WHERE p.word_id = ?
                    ORDER BY p.likes_count DESC, p.created_at DESC
                """, (word_id,))
            else:
                cursor.execute("""
                    SELECT p.id, p.user_id as userId, p.text, p.likes_count as likes, 
                           p.created_at, p.word_id,
                           u.name as author, u.initials, u.age, u.type
                    FROM posts p
                    JOIN users u ON p.user_id = u.id
                    ORDER BY p.likes_count DESC, p.created_at DESC
                """)
            posts = [dict_from_row(row) for row in cursor.fetchall()]
            
            result = []
            for post in posts:
                cursor.execute("SELECT media_type as type, url FROM post_media WHERE post_id = ?", (post['id'],))
                media = [dict_from_row(row) for row in cursor.fetchall()]
                
                cursor.execute("""
                    SELECT c.id, c.user_id as userId, c.text, c.created_at, c.likes_count,
                           u.name as author, u.initials, u.type
                    FROM comments c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.post_id = ?
                    ORDER BY c.likes_count DESC, c.created_at DESC
                """, (post['id'],))
                comments_raw = [dict_from_row(row) for row in cursor.fetchall()]
                
                comments_with_liked = []
                for c in comments_raw:
                    cursor.execute("SELECT 1 FROM comment_likes WHERE comment_id = ? AND user_id = ?", (c['id'], user_id))
                    comment_liked = cursor.fetchone() is not None
                    comments_with_liked.append({
                        'id': c['id'],
                        'userId': c['userId'],
                        'author': c['author'],
                        'initials': c['initials'],
                        'type': c['type'],
                        'text': c['text'],
                        'likes': c['likes_count'],
                        'liked': comment_liked,
                        'time': format_time_ago(c['created_at'])
                    })
                
                cursor.execute("SELECT 1 FROM likes WHERE post_id = ? AND user_id = ?", (post['id'], user_id))
                liked = cursor.fetchone() is not None
                
                cursor.execute("SELECT id, question FROM polls WHERE post_id = ?", (post['id'],))
                poll_row = cursor.fetchone()
                poll_data = None
                if poll_row:
                    poll = dict_from_row(poll_row)
                    cursor.execute("SELECT id, text, votes_count FROM poll_options WHERE poll_id = ? ORDER BY votes_count DESC", (poll['id'],))
                    options = [dict_from_row(row) for row in cursor.fetchall()]
                    
                    cursor.execute("SELECT option_id FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll['id'], user_id))
                    vote_row = cursor.fetchone()
                    user_vote = vote_row[0] if vote_row else None
                    
                    total_votes = sum(opt['votes_count'] for opt in options)
                    
                    poll_data = {
                        'id': poll['id'],
                        'question': poll['question'],
                        'options': [{
                            'id': opt['id'],
                            'text': opt['text'],
                            'votes': opt['votes_count'],
                            'percentage': round((opt['votes_count'] / total_votes * 100) if total_votes > 0 else 0)
                        } for opt in options],
                        'totalVotes': total_votes,
                        'userVote': user_vote
                    }
                
                result.append({
                    'id': post['id'],
                    'userId': post['userId'],
                    'author': post['author'],
                    'initials': post['initials'],
                    'age': post['age'],
                    'type': post['type'],
                    'text': post['text'],
                    'media': media,
                    'likes': post['likes'],
                    'liked': liked,
                    'time': format_time_ago(post['created_at']),
                    'comments': comments_with_liked,
                    'poll': poll_data
                })
            
            return jsonify(result)
            
        except sqlite3.Error as err:
            print(f"Error getting posts: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/posts', methods=['POST'])
    def create_post():
        data = request.json
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1 FROM users WHERE id = ?", (data['userId'],))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO users (id, name, initials, age, type) VALUES (?, ?, ?, ?, ?)",
                    (data['userId'], data['author'], data['initials'], data['age'], data['type'])
                )
            
            post_id = f"post-{secrets.token_hex(8)}"
            word_id = data.get('wordId')
            
            cursor.execute(
                "INSERT INTO posts (id, user_id, word_id, text) VALUES (?, ?, ?, ?)",
                (post_id, data['userId'], word_id, data.get('text', ''))
            )
            
            for media in data.get('media', []):
                cursor.execute(
                    "INSERT INTO post_media (post_id, media_type, url) VALUES (?, ?, ?)",
                    (post_id, media['type'], media['url'])
                )
            
            poll_data = None
            if data.get('poll'):
                poll_id = f"poll-{secrets.token_hex(4)}"
                cursor.execute(
                    "INSERT INTO polls (id, post_id, question) VALUES (?, ?, ?)",
                    (poll_id, post_id, data['poll']['question'])
                )
                
                options = []
                for i, opt_text in enumerate(data['poll']['options']):
                    opt_id = f"opt-{secrets.token_hex(4)}"
                    cursor.execute(
                        "INSERT INTO poll_options (id, poll_id, text, votes_count) VALUES (?, ?, ?, 0)",
                        (opt_id, poll_id, opt_text)
                    )
                    options.append({
                        'id': opt_id,
                        'text': opt_text,
                        'votes': 0,
                        'percentage': 0
                    })
                
                poll_data = {
                    'id': poll_id,
                    'question': data['poll']['question'],
                    'options': options,
                    'totalVotes': 0,
                    'userVote': None
                }
            
            conn.commit()
            
            return jsonify({
                'id': post_id,
                'userId': data['userId'],
                'author': data['author'],
                'initials': data['initials'],
                'age': data['age'],
                'type': data['type'],
                'text': data.get('text', ''),
                'media': data.get('media', []),
                'likes': 0,
                'liked': False,
                'time': 'Just now',
                'comments': [],
                'poll': poll_data
            }), 201
            
        except sqlite3.Error as err:
            print(f"Error creating post: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/posts/<post_id>', methods=['PUT'])
    def update_post(post_id):
        data = request.json
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE posts SET text = ? WHERE id = ?",
                (data.get('text', ''), post_id)
            )
            
            cursor.execute("DELETE FROM post_media WHERE post_id = ?", (post_id,))
            for media in data.get('media', []):
                cursor.execute(
                    "INSERT INTO post_media (post_id, media_type, url) VALUES (?, ?, ?)",
                    (post_id, media['type'], media['url'])
                )
            
            conn.commit()
            return jsonify({'success': True})
            
        except sqlite3.Error as err:
            print(f"Error updating post: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/posts/<post_id>', methods=['DELETE'])
    def delete_post(post_id):
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            conn.commit()
            return jsonify({'success': True})
            
        except sqlite3.Error as err:
            print(f"Error deleting post: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/posts/<post_id>/like', methods=['POST'])
    def toggle_like(post_id):
        data = request.json
        user_id = data.get('userId', 'user-matt')
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1 FROM likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
            already_liked = cursor.fetchone() is not None
            
            if already_liked:
                cursor.execute("DELETE FROM likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
                cursor.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
                liked = False
            else:
                cursor.execute("INSERT INTO likes (post_id, user_id) VALUES (?, ?)", (post_id, user_id))
                cursor.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
                liked = True
                
                cursor.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,))
                post_owner = cursor.fetchone()
                if post_owner and post_owner[0] != user_id:
                    cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
                    actor = cursor.fetchone()
                    actor_name = actor[0] if actor else 'Someone'
                    cursor.execute(
                        "INSERT INTO notifications (user_id, type, actor_id, actor_name, post_id, message) VALUES (?, ?, ?, ?, ?, ?)",
                        (post_owner[0], 'post_like', user_id, actor_name, post_id, f'{actor_name} liked your post')
                    )
            
            conn.commit()
            
            cursor.execute("SELECT likes_count FROM posts WHERE id = ?", (post_id,))
            result = cursor.fetchone()
            likes = result[0] if result else 0
            
            return jsonify({'likes': likes, 'liked': liked})
            
        except sqlite3.Error as err:
            print(f"Error toggling like: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/posts/<post_id>/comments', methods=['POST'])
    def add_comment(post_id):
        data = request.json
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1 FROM users WHERE id = ?", (data['userId'],))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO users (id, name, initials, age, type) VALUES (?, ?, ?, ?, ?)",
                    (data['userId'], data['author'], data['initials'], data.get('age', 18), data['type'])
                )
            
            comment_id = f"c-{secrets.token_hex(4)}"
            
            cursor.execute(
                "INSERT INTO comments (id, post_id, user_id, text) VALUES (?, ?, ?, ?)",
                (comment_id, post_id, data['userId'], data['text'])
            )
            
            cursor.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,))
            post_owner = cursor.fetchone()
            if post_owner and post_owner[0] != data['userId']:
                cursor.execute(
                    "INSERT INTO notifications (user_id, type, actor_id, actor_name, post_id, comment_id, message) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (post_owner[0], 'comment', data['userId'], data['author'], post_id, comment_id, f"{data['author']} commented on your post")
                )
            
            conn.commit()
            
            return jsonify({
                'id': comment_id,
                'userId': data['userId'],
                'author': data['author'],
                'initials': data['initials'],
                'type': data['type'],
                'text': data['text'],
                'likes': 0,
                'liked': False,
                'time': 'Just now'
            }), 201
            
        except sqlite3.Error as err:
            print(f"Error adding comment: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/posts/<post_id>/comments/<comment_id>', methods=['PUT'])
    def update_comment(post_id, comment_id):
        data = request.json
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE comments SET text = ? WHERE id = ? AND post_id = ?",
                (data.get('text', ''), comment_id, post_id)
            )
            conn.commit()
            return jsonify({'success': True})
            
        except sqlite3.Error as err:
            print(f"Error updating comment: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/posts/<post_id>/comments/<comment_id>', methods=['DELETE'])
    def delete_comment(post_id, comment_id):
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM comments WHERE id = ? AND post_id = ?", (comment_id, post_id))
            conn.commit()
            return jsonify({'success': True})
            
        except sqlite3.Error as err:
            print(f"Error deleting comment: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/posts/<post_id>/comments/<comment_id>/like', methods=['POST'])
    def toggle_comment_like(post_id, comment_id):
        data = request.json
        user_id = data.get('userId', 'user-matt')
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1 FROM comment_likes WHERE comment_id = ? AND user_id = ?", (comment_id, user_id))
            already_liked = cursor.fetchone() is not None
            
            if already_liked:
                cursor.execute("DELETE FROM comment_likes WHERE comment_id = ? AND user_id = ?", (comment_id, user_id))
                cursor.execute("UPDATE comments SET likes_count = likes_count - 1 WHERE id = ?", (comment_id,))
                liked = False
            else:
                cursor.execute("INSERT INTO comment_likes (comment_id, user_id) VALUES (?, ?)", (comment_id, user_id))
                cursor.execute("UPDATE comments SET likes_count = likes_count + 1 WHERE id = ?", (comment_id,))
                liked = True
                
                cursor.execute("SELECT user_id FROM comments WHERE id = ?", (comment_id,))
                comment_owner = cursor.fetchone()
                if comment_owner and comment_owner[0] != user_id:
                    cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
                    actor = cursor.fetchone()
                    actor_name = actor[0] if actor else 'Someone'
                    cursor.execute(
                        "INSERT INTO notifications (user_id, type, actor_id, actor_name, post_id, comment_id, message) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (comment_owner[0], 'comment_like', user_id, actor_name, post_id, comment_id, f'{actor_name} liked your comment')
                    )
            
            conn.commit()
            
            cursor.execute("SELECT likes_count FROM comments WHERE id = ?", (comment_id,))
            result = cursor.fetchone()
            likes = result[0] if result else 0
            
            return jsonify({'likes': likes, 'liked': liked})
            
        except sqlite3.Error as err:
            print(f"Error toggling comment like: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/polls/<poll_id>/vote', methods=['POST'])
    def vote_poll(poll_id):
        data = request.json
        user_id = data.get('userId', 'user-matt')
        option_id = data.get('optionId')
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT option_id FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
            existing_vote = cursor.fetchone()
            
            is_new_vote = existing_vote is None
            
            if existing_vote:
                old_option_id = existing_vote[0]
                if old_option_id == option_id:
                    return jsonify({'error': 'Already voted for this option'}), 400
                cursor.execute("UPDATE poll_options SET votes_count = votes_count - 1 WHERE id = ?", (old_option_id,))
                cursor.execute("UPDATE poll_votes SET option_id = ? WHERE poll_id = ? AND user_id = ?", (option_id, poll_id, user_id))
            else:
                cursor.execute("INSERT INTO poll_votes (poll_id, option_id, user_id) VALUES (?, ?, ?)", (poll_id, option_id, user_id))
            
            cursor.execute("UPDATE poll_options SET votes_count = votes_count + 1 WHERE id = ?", (option_id,))
            
            if is_new_vote:
                cursor.execute("""
                    SELECT p.user_id, pl.question 
                    FROM polls pl 
                    JOIN posts p ON pl.post_id = p.id 
                    WHERE pl.id = ?
                """, (poll_id,))
                poll_info = cursor.fetchone()
                if poll_info and poll_info[0] != user_id:
                    post_owner_id = poll_info[0]
                    poll_question = poll_info[1]
                    cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
                    actor = cursor.fetchone()
                    actor_name = actor[0] if actor else 'Someone'
                    cursor.execute("SELECT post_id FROM polls WHERE id = ?", (poll_id,))
                    post_row = cursor.fetchone()
                    post_id = post_row[0] if post_row else None
                    cursor.execute(
                        "INSERT INTO notifications (user_id, type, actor_id, actor_name, post_id, message) VALUES (?, ?, ?, ?, ?, ?)",
                        (post_owner_id, 'poll_vote', user_id, actor_name, post_id, f'{actor_name} voted on your poll')
                    )
            
            conn.commit()
            
            cursor.execute("SELECT id, text, votes_count FROM poll_options WHERE poll_id = ? ORDER BY votes_count DESC", (poll_id,))
            options = [dict_from_row(row) for row in cursor.fetchall()]
            total_votes = sum(opt['votes_count'] for opt in options)
            
            return jsonify({
                'options': [{
                    'id': opt['id'],
                    'text': opt['text'],
                    'votes': opt['votes_count'],
                    'percentage': round((opt['votes_count'] / total_votes * 100) if total_votes > 0 else 0)
                } for opt in options],
                'totalVotes': total_votes,
                'userVote': option_id
            })
            
        except sqlite3.Error as err:
            print(f"Error voting on poll: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/posts/search', methods=['GET'])
    def search_posts():
        query = request.args.get('q', '').strip()
        user_id = request.args.get('userId', 'user-matt')
        word_id = request.args.get('wordId', type=int)
        
        if not query or len(query) < 2:
            return jsonify([])
        
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            
            if word_id:
                cursor.execute("""
                    SELECT p.id, p.user_id as userId, p.text, p.likes_count as likes, 
                           p.created_at, p.word_id,
                           u.name as author, u.initials, u.age, u.type
                    FROM posts p
                    JOIN users u ON p.user_id = u.id
                    WHERE p.text LIKE ? AND p.word_id = ?
                    ORDER BY p.likes_count DESC, p.created_at DESC
                """, (search_pattern, word_id))
            else:
                cursor.execute("""
                    SELECT p.id, p.user_id as userId, p.text, p.likes_count as likes, 
                           p.created_at, p.word_id,
                           u.name as author, u.initials, u.age, u.type
                    FROM posts p
                    JOIN users u ON p.user_id = u.id
                    WHERE p.text LIKE ?
                    ORDER BY p.likes_count DESC, p.created_at DESC
                """, (search_pattern,))
            posts_data = [dict_from_row(row) for row in cursor.fetchall()]
            
            result = []
            for post in posts_data:
                cursor.execute("SELECT media_type as type, url FROM post_media WHERE post_id = ?", (post['id'],))
                media = [dict_from_row(row) for row in cursor.fetchall()]
                
                cursor.execute("""
                    SELECT c.id, c.user_id as userId, c.text, c.created_at, c.likes_count,
                           u.name as author, u.initials, u.type
                    FROM comments c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.post_id = ?
                    ORDER BY c.likes_count DESC, c.created_at DESC
                """, (post['id'],))
                comments_raw = [dict_from_row(row) for row in cursor.fetchall()]
                
                comments_with_liked = []
                for c in comments_raw:
                    cursor.execute("SELECT 1 FROM comment_likes WHERE comment_id = ? AND user_id = ?", (c['id'], user_id))
                    comment_liked = cursor.fetchone() is not None
                    comments_with_liked.append({
                        'id': c['id'],
                        'userId': c['userId'],
                        'author': c['author'],
                        'initials': c['initials'],
                        'type': c['type'],
                        'text': c['text'],
                        'likes': c['likes_count'],
                        'liked': comment_liked,
                        'time': format_time_ago(c['created_at'])
                    })
                
                cursor.execute("SELECT 1 FROM likes WHERE post_id = ? AND user_id = ?", (post['id'], user_id))
                liked = cursor.fetchone() is not None
                
                cursor.execute("SELECT id, question FROM polls WHERE post_id = ?", (post['id'],))
                poll_row = cursor.fetchone()
                poll_data = None
                if poll_row:
                    poll = dict_from_row(poll_row)
                    cursor.execute("SELECT id, text, votes_count FROM poll_options WHERE poll_id = ? ORDER BY votes_count DESC", (poll['id'],))
                    options = [dict_from_row(row) for row in cursor.fetchall()]
                    cursor.execute("SELECT option_id FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll['id'], user_id))
                    vote_row = cursor.fetchone()
                    user_vote = vote_row[0] if vote_row else None
                    total_votes = sum(opt['votes_count'] for opt in options)
                    poll_data = {
                        'id': poll['id'],
                        'question': poll['question'],
                        'options': [{
                            'id': opt['id'],
                            'text': opt['text'],
                            'votes': opt['votes_count'],
                            'percentage': round((opt['votes_count'] / total_votes * 100) if total_votes > 0 else 0)
                        } for opt in options],
                        'totalVotes': total_votes,
                        'userVote': user_vote
                    }
                
                result.append({
                    'id': post['id'],
                    'userId': post['userId'],
                    'author': post['author'],
                    'initials': post['initials'],
                    'age': post['age'],
                    'type': post['type'],
                    'text': post['text'],
                    'media': media,
                    'likes': post['likes'],
                    'liked': liked,
                    'time': format_time_ago(post['created_at']),
                    'comments': comments_with_liked,
                    'poll': poll_data
                })
            
            return jsonify(result)
            
        except sqlite3.Error as err:
            print(f"Error searching posts: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/notifications', methods=['GET'])
    def get_notifications():
        user_id = request.args.get('userId', 'user-matt')
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, type, actor_id, actor_name, post_id, comment_id, message, read, created_at
                FROM notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 20
            """, (user_id,))
            
            notifications = []
            for row in cursor.fetchall():
                notifications.append({
                    'id': row[0],
                    'type': row[1],
                    'actorId': row[2],
                    'actorName': row[3],
                    'postId': row[4],
                    'commentId': row[5],
                    'message': row[6],
                    'read': bool(row[7]),
                    'time': format_time_ago(row[8])
                })
            
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read = 0", (user_id,))
            unread_count = cursor.fetchone()[0]
            
            return jsonify({
                'notifications': notifications,
                'unreadCount': unread_count
            })
            
        except sqlite3.Error as err:
            print(f"Error getting notifications: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
    def mark_notification_read(notification_id):
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET read = 1 WHERE id = ?", (notification_id,))
            conn.commit()
            return jsonify({'success': True})
            
        except sqlite3.Error as err:
            print(f"Error marking notification read: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/notifications/read-all', methods=['POST'])
    def mark_all_notifications_read():
        data = request.json
        user_id = data.get('userId', 'user-matt')
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET read = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            return jsonify({'success': True})
            
        except sqlite3.Error as err:
            print(f"Error marking all notifications read: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()

    @app.route('/api/notifications/clear-all', methods=['POST'])
    def clear_all_notifications():
        data = request.json
        user_id = data.get('userId', 'user-matt')
        conn = get_db()
        
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
            conn.commit()
            return jsonify({'success': True})
            
        except sqlite3.Error as err:
            print(f"Error clearing all notifications: {err}")
            return jsonify({'error': str(err)}), 500
        finally:
            conn.close()