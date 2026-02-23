from flask import Flask, render_template, request
import secrets
from datetime import datetime

from database import init_database, get_db
from routes import register_routes

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


def get_all_words():
    conn = get_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, word, phonetic, description, challenge, date 
            FROM word_of_day 
            ORDER BY date DESC
        """)
        results = cursor.fetchall()
        return [{
            'id': row[0],
            'word': row[1],
            'phonetic': row[2],
            'description': row[3],
            'challenge': row[4],
            'date': row[5]
        } for row in results]
    except Exception as e:
        print(f"Error getting words: {e}")
        return []
    finally:
        conn.close()


def get_word_by_id(word_id):
    conn = get_db()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, word, phonetic, description, challenge, date 
            FROM word_of_day 
            WHERE id = ?
        """, (word_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                'id': result[0],
                'word': result[1],
                'phonetic': result[2],
                'description': result[3],
                'challenge': result[4],
                'date': result[5]
            }
        return None
    except Exception as e:
        print(f"Error getting word: {e}")
        return None
    finally:
        conn.close()


def get_latest_word():
    conn = get_db()
    if not conn:
        return {
            'id': 1,
            'word': 'Ang Mo',
            'phonetic': '[ ahng moh ]',
            'description': 'A colloquial Hokkien term used in Singapore.',
            'challenge': 'Share your thoughts about this word!',
            'date': '2025-01-28'
        }
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, word, phonetic, description, challenge, date 
            FROM word_of_day 
            ORDER BY date DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        if result:
            return {
                'id': result[0],
                'word': result[1],
                'phonetic': result[2],
                'description': result[3],
                'challenge': result[4],
                'date': result[5]
            }
        else:
            return {
                'id': 1,
                'word': 'Ang Mo',
                'phonetic': '[ ahng moh ]',
                'description': 'A colloquial Hokkien term used in Singapore.',
                'challenge': 'Share your thoughts about this word!',
                'date': '2025-01-28'
            }
    except Exception as e:
        print(f"Error getting word of day: {e}")
        return {
            'id': 1,
            'word': 'Ang Mo',
            'phonetic': '[ ahng moh ]',
            'description': 'A colloquial Hokkien term used in Singapore.',
            'challenge': 'Share your thoughts about this word!',
            'date': '2025-01-28'
        }
    finally:
        conn.close()


@app.route('/')
@app.route('/youth/feed')
def youth_feed():
    word_id = request.args.get('word_id', type=int)
    
    if word_id:
        word_of_day = get_word_by_id(word_id)
        if not word_of_day:
            word_of_day = get_latest_word()
    else:
        word_of_day = get_latest_word()
    
    current_user = {
        'id': 'user-matt',
        'name': 'Matthew Ico',
        'initials': 'MI',
        'age': 17,
        'type': 'youth'
    }
    
    return render_template('feed.html',
        version='youth',
        current_user=current_user,
        word_of_day=word_of_day,
        all_words=get_all_words(),
        today=datetime.now().strftime('%A, %B %d, %Y')
    )


@app.route('/elderly/feed')
def elderly_feed():
    word_id = request.args.get('word_id', type=int)
    
    if word_id:
        word_of_day = get_word_by_id(word_id)
        if not word_of_day:
            word_of_day = get_latest_word()
    else:
        word_of_day = get_latest_word()
    
    current_user = {
        'id': 'user-matt-senior',
        'name': 'Matthew Ico',
        'initials': 'MI',
        'age': 65,
        'type': 'senior'
    }
    
    return render_template('feed.html',
        version='elderly',
        current_user=current_user,
        word_of_day=word_of_day,
        all_words=get_all_words(),
        today=datetime.now().strftime('%A, %B %d, %Y')
    )

register_routes(app)

init_database()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)