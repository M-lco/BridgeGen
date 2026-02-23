import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'bridgegen.db')


def get_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as err:
        print(f"Database connection error: {err}")
        return None


def init_database():
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                initials TEXT NOT NULL,
                age INTEGER NOT NULL CHECK (age >= 1 AND age <= 120),
                type TEXT NOT NULL CHECK (type IN ('youth', 'senior')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_of_day (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                phonetic TEXT,
                description TEXT,
                challenge TEXT,
                date DATE UNIQUE NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                word_id INTEGER,
                text TEXT,
                likes_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (word_id) REFERENCES word_of_day(id) ON DELETE SET NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video')),
                url TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                text TEXT NOT NULL,
                likes_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (post_id, user_id),
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comment_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (comment_id, user_id),
                FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                question TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS poll_options (
                id TEXT PRIMARY KEY,
                poll_id TEXT NOT NULL,
                text TEXT NOT NULL,
                votes_count INTEGER DEFAULT 0,
                FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS poll_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id TEXT NOT NULL,
                option_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (poll_id, user_id),
                FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE,
                FOREIGN KEY (option_id) REFERENCES poll_options(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                post_id TEXT,
                comment_id TEXT,
                message TEXT NOT NULL,
                read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                post_id TEXT,
                comment_id TEXT,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        insert_sample_data(cursor, conn)
        
    except sqlite3.Error as err:
        print(f"SQLite Error: {err}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()


def insert_sample_data(cursor, conn):
    cursor.execute("SELECT COUNT(*) FROM users")
    result = cursor.fetchone()
    if result[0] > 0:
        return
    
    users = [
        ('user-matt', 'Matthew Ico', 'MI', 17, 'youth'),
        ('user-matt-senior', 'Matthew Ico', 'MI', 65, 'senior'),
        ('user-1', 'Joel Lim', 'JL', 19, 'youth'),
        ('user-2', 'Auntie Helen', 'AH', 68, 'senior'),
        ('user-3', 'Maya Ng', 'MN', 22, 'youth'),
        ('user-4', 'Ryan Tan', 'RT', 17, 'youth'),
        ('user-5', 'Auntie Lily', 'AL', 65, 'senior'),
        ('user-6', 'Sarah Lee', 'SL', 20, 'youth'),
        ('user-7', 'Uncle Chen', 'UC', 72, 'senior')
    ]
    cursor.executemany(
        "INSERT INTO users (id, name, initials, age, type) VALUES (?, ?, ?, ?, ?)",
        users
    )
    
    words = [
        ('Ang Mo', '[ ahng moh ]', 'A colloquial Hokkien term used in Singapore to refer to Caucasian people. Literally translates to "red hair" in Hokkien.', 'Share the origin of this word, tell us a memory about it, or teach us how to pronounce it correctly!', '2025-01-28'),
        ('Shiok', '[ shee-awk ]', 'A Singlish expression meaning extremely enjoyable, pleasurable, or satisfying. Often used to describe delicious food or a great experience.', 'Share a moment when you felt "shiok" - what made it so satisfying?', '2025-01-27'),
        ('Kiasu', '[ kee-ah-soo ]', 'A Hokkien term meaning "afraid to lose". Describes the competitive, always-want-to-be-first mentality common in Singaporean culture.', 'Are you kiasu? Share a funny kiasu story or moment you witnessed!', '2025-01-26'),
        ('Makan', '[ mah-kahn ]', 'A Malay word meaning "to eat". Commonly used in Singapore to refer to food or the act of eating.', 'What is your favorite makan spot? Share your go-to hawker stall or restaurant!', '2025-01-25'),
        ('Paiseh', '[ pie-seh ]', 'A Hokkien term meaning embarrassed, shy, or feeling apologetic. Used when you feel awkward or want to express mild apology.', 'Share a paiseh moment - when did you feel most embarrassed?', '2025-01-24'),
        ('Boleh', '[ boh-leh ]', 'A Malay word meaning "can" or "possible". Often used to ask if something is allowed or achievable.', 'Singapore boleh! Share something that makes you proud of Singapore!', '2025-01-23'),
        ('Lepak', '[ leh-pahk ]', 'A Malay slang term meaning to relax, hang out, or chill without any specific purpose.', 'Where is your favorite place to lepak? Share your chill spot!', '2025-01-22')
    ]
    cursor.executemany(
        "INSERT INTO word_of_day (word, phonetic, description, challenge, date) VALUES (?, ?, ?, ?, ?)",
        words
    )
    
    posts = [
        # Ang Mo (word_id=1) - 6 posts
        # Format: (id, user_id, word_id, text, likes)
        ('post-1', 'user-5', 1, "In the 1960s, we also called them 'mat salleh'. The term 'ang mo' literally means 'red hair' in Hokkien. Back then, seeing one was quite rare! Now Singapore is so diverse - it's wonderful!", 89),
        ('post-2', 'user-3', 1, 'Overheard at the kopitiam: "Wah that ang mo speak Hokkien better than my grandson!" The look on the uncle\'s face was priceless!', 76),
        ('post-3', 'user-1', 1, "At the hawker centre, the ang mo uncle tried ordering chicken rice in Singlish and everyone couldn't help but smile at his enthusiasm!", 54),
        ('post-4', 'user-7', 1, "Last time at Chinatown, one ang mo tourist asked me for directions in perfect Cantonese! I was so shocked I replied him in English instead. He laughed and we ended up chatting for an hour about old Singapore.", 47),
        ('post-5', 'user-4', 1, 'My ang mo friend asked me why we call them "red hair" when most of them don\'t even have red hair. Had to explain it\'s a historical thing from when Dutch traders came to Southeast Asia!', 38),
        ('post-6', 'user-2', 1, "When I was young, seeing an ang mo was so rare! We would all stop and stare. Now my grandson's best friend is ang mo and they talk in a mix of English and Singlish. Times have changed!", 31),
        
        # Shiok (word_id=2) - 7 posts
        ('post-7', 'user-6', 2, "Finally finished my finals! That shiok feeling of freedom is unmatched 🎉 Going to sleep for 12 hours straight!", 92),
        ('post-8', 'user-4', 2, "Ice cold teh peng on a hot afternoon. The feeling when that first sip hits... pure shiok! Nothing else comes close.", 71),
        ('post-9', 'user-7', 2, "Aircon on full blast after walking in the hot sun. That feeling when the cold air hits your face - SHIOK!", 58),
        ('post-10', 'user-1', 2, "That first bite of chilli crab after a long day... SHIOK! Nothing beats seafood by the beach with good company.", 49),
        ('post-11', 'user-3', 2, "Getting into bed with fresh clean sheets after a long week. Maximum shiok achieved!", 41),
        ('post-12', 'user-2', 2, "My late husband used to say 'shiok' whenever I made his favorite curry. Now every time I cook it, I think of him and smile.", 36),
        ('post-13', 'user-5', 2, "Swimming in the pool on a Sunday morning when nobody else is there. So peaceful, so shiok!", 24),
        
        # Kiasu (word_id=3) - 6 posts
        ('post-14', 'user-1', 3, "My mom woke up at 5am just to queue for bubble tea because got 1-for-1. The kiasu is strong in my family 😂 She bought 10 cups!", 83),
        ('post-15', 'user-3', 3, "Saw someone chope 5 tables at the hawker center with tissue packets. Peak kiasu behavior! One person need so many tables for what?", 67),
        ('post-16', 'user-6', 3, "Parents already signing up kids for tuition before they even start Primary 1. Singapore kiasu culture is real!", 52),
        ('post-17', 'user-5', 3, "I admit I'm kiasu when it comes to buffet. Must get my money's worth! Always head straight for the seafood section first.", 44),
        ('post-18', 'user-7', 3, "Back in my day, we didn't have this kiasu culture. Now everyone rushing here and there. Sometimes slow down is better lah!", 33),
        ('post-19', 'user-4', 3, "Queue for new iPhone started 3 days early. I respect the dedication but that's next level kiasu!", 21),
        
        # Makan (word_id=4) - 7 posts
        ('post-20', 'user-4', 4, "Maxwell Food Centre chicken rice is still the best makan spot. The queue is long but worth every minute. Fight me.", 78),
        ('post-21', 'user-7', 4, "Old Airport Road hawker centre. Been going there since 1970s. The char kway teow uncle still remembers my order after 50 years!", 65),
        ('post-22', 'user-6', 4, "Just discovered this hidden gem in Tiong Bahru - the laksa there is amazing! Who wants to makan together this weekend?", 53),
        ('post-23', 'user-1', 4, "Nothing like 2am prata after clubbing. The best makan is always when you're hungry at weird hours!", 46),
        ('post-24', 'user-2', 4, "Nothing like home-cooked makan. My grandmother's recipes are still the best after 50 years. Secret ingredient is always love.", 39),
        ('post-25', 'user-3', 4, "Took my overseas friends to Newton Food Centre. They couldn't believe how good and cheap the food is. Proud of our makan culture!", 28),
        ('post-26', 'user-5', 4, "Sunday family makan at dim sum restaurant. Three generations sitting together, this is what life is about!", 22),
        
        # Paiseh (word_id=5) - 6 posts
        ('post-27', 'user-3', 5, "Accidentally called my prof 'mom' in front of the whole lecture hall. So paiseh I wanted to disappear into the floor 😭", 95),
        ('post-28', 'user-1', 5, "Waved back at someone who wasn't waving at me. The paiseh walk of shame afterwards... I still think about it at night.", 72),
        ('post-29', 'user-6', 5, "Sent a complaint about my boss... TO my boss. Wrong chat. Most paiseh moment of my career. Had to take MC the next day 😅", 61),
        ('post-30', 'user-4', 5, "Walked into glass door at MBS in front of tourists. Security guard tried not to laugh. Maximum paiseh!", 48),
        ('post-31', 'user-5', 5, "Still remember 40 years ago, I tripped and fell in front of my crush. So paiseh! But he helped me up - now he's my husband of 38 years 💕", 37),
        ('post-32', 'user-2', 5, "Called the wrong person 'Auntie' at the market. She was younger than me! So paiseh, I just quickly walk away.", 26),
        
        # Boleh (word_id=6) - 5 posts
        ('post-33', 'user-6', 6, "Just watched Singapore win gold at SEA Games. Proud moment! Our athletes showed everyone - Singapore boleh! 🇸🇬🥇", 81),
        ('post-34', 'user-2', 6, "From third world to first world in one generation. Our founding fathers showed us Singapore boleh! We should never forget.", 63),
        ('post-35', 'user-4', 6, "Singapore's public transport system is world-class. Anywhere also can go. Clean, efficient, affordable. Singapore boleh!", 47),
        ('post-36', 'user-1', 6, "Small country but we got F1, world's best airport, amazing food. Don't underestimate us - Singapore boleh!", 35),
        ('post-37', 'user-7', 6, "Survived Japanese occupation, konfrontasi, separation from Malaysia. Our generation showed Singapore boleh. Now young people continue!", 29),
        
        # Lepak (word_id=7) - 6 posts
        ('post-38', 'user-3', 7, "East Coast Park at sunset is my favorite lepak spot. Just sit there, eat satay, watch the sea, forget all problems.", 74),
        ('post-39', 'user-1', 7, "Nothing beats lepaking at the mamak with friends until 3am talking about everything and nothing. Best therapy!", 59),
        ('post-40', 'user-6', 7, "Found this quiet spot at Botanic Gardens. Perfect for lepak and reading. No wifi, no distraction, just peace.", 45),
        ('post-41', 'user-7', 7, "My generation lepak at void deck play chess and drink kopi. Now young people lepak at cafe pay $8 for coffee. Times change!", 38),
        ('post-42', 'user-4', 7, "Lepaking at home watching Netflix is underrated. Don't need to go anywhere, just enjoy the aircon!", 27),
        ('post-43', 'user-5', 7, "Best lepak is at the coffeeshop with old friends. Talk about old times, complain about young people. Shiok!", 19)
    ]
    cursor.executemany(
        "INSERT INTO posts (id, user_id, word_id, text, likes_count) VALUES (?, ?, ?, ?, ?)",
        posts
    )
    
    comments = [
        # Format: (id, post_id, user_id, text, likes_count)
        # Ang Mo comments - post likes: 89, 76, 54, 47, 38, 31
        ('c1', 'post-1', 'user-4', "Wow, I never knew it meant 'red hair'! Thanks for sharing the history!", 14),
        ('c2', 'post-1', 'user-6', 'My grandma uses this word all the time! Now I finally understand the origin.', 9),
        ('c3', 'post-2', 'user-2', "Haha! That uncle must have been so proud. It shows how much people love our culture!", 11),
        ('c4', 'post-2', 'user-1', 'This is exactly why I love Singapore! So multicultural.', 7),
        ('c5', 'post-3', 'user-5', "That's very heartwarming. Shows how welcoming Singaporeans are!", 8),
        ('c6', 'post-4', 'user-3', 'Uncle, your stories are always the best! Please share more.', 6),
        ('c7', 'post-6', 'user-1', "Auntie Helen, that's such a beautiful observation about how times have changed!", 5),
        ('c8', 'post-6', 'user-4', 'Learning so much from our seniors! This is what BridgeGen is for.', 4),
        
        # Shiok comments - post likes: 92, 71, 58, 49, 41, 36, 24
        ('c9', 'post-7', 'user-2', 'Congrats on finishing your finals! You deserve the rest.', 15),
        ('c10', 'post-7', 'user-4', 'That feeling is the BEST. Enjoy your freedom!', 10),
        ('c11', 'post-8', 'user-5', 'Teh peng is life! I drink it every single morning without fail.', 11),
        ('c12', 'post-8', 'user-3', 'Try adding lime - teh peng limau. Next level shiok!', 8),
        ('c13', 'post-10', 'user-7', 'Try the one at East Coast! Been going there for 30 years. Still the best.', 7),
        ('c14', 'post-10', 'user-3', 'Chilli crab is life! Where do you usually go? Share the spot!', 5),
        ('c15', 'post-12', 'user-1', 'Auntie, this is so sweet 🥺 Your husband was lucky to have you!', 6),
        ('c16', 'post-12', 'user-3', 'The best love stories come from the simplest moments. Thank you for sharing.', 4),
        
        # Kiasu comments - post likes: 83, 67, 52, 44, 33, 21
        ('c17', 'post-14', 'user-6', 'Your mom is goals 😂 Did she manage to get the bubble tea?', 12),
        ('c18', 'post-14', 'user-7', 'Wah 10 cups! That one very kiasu already! But also very sweet lah.', 9),
        ('c19', 'post-15', 'user-2', 'Last time no need to chope. People more considerate in the old days.', 10),
        ('c20', 'post-15', 'user-4', '5 tables is too much lah. One or two can understand, but five??', 7),
        ('c21', 'post-16', 'user-5', 'This is why our children so stressed. Let them be kids first!', 8),
        ('c22', 'post-18', 'user-4', 'Uncle, you are right. We should learn to slow down and enjoy life.', 5),
        ('c23', 'post-18', 'user-1', 'Wise words! Sometimes the kiasu mentality hurts us more than helps.', 4),
        
        # Makan comments - post likes: 78, 65, 53, 46, 39, 28, 22
        ('c24', 'post-20', 'user-7', 'Tian Tian or Ah Tai? This is the real chicken rice debate!', 13),
        ('c25', 'post-20', 'user-3', 'Both also good lah! Why must fight? Just eat and enjoy!', 9),
        ('c26', 'post-21', 'user-4', 'Uncle, that char kway teow uncle is legendary! 50 years is amazing.', 10),
        ('c27', 'post-21', 'user-6', 'Old Airport Road is hawker heaven! So many good stalls there.', 7),
        ('c28', 'post-22', 'user-1', 'Where in Tiong Bahru? Must go try! Drop the location!', 8),
        ('c29', 'post-24', 'user-5', 'Auntie, can share your grandmother recipe? My cooking cannot make it 😅', 6),
        ('c30', 'post-26', 'user-7', "That's what I love about Singapore - food brings everyone together!", 3),
        
        # Paiseh comments - post likes: 95, 72, 61, 48, 37, 26
        ('c31', 'post-27', 'user-5', "Don't worry dear, everyone makes mistakes! Your prof probably forgot already.", 16),
        ('c32', 'post-27', 'user-4', 'HAHAHA I did this before too! Called my teacher "daddy" once. So paiseh!', 19),
        ('c33', 'post-28', 'user-2', 'This happens to everyone lah! 😂 Part of life.', 11),
        ('c34', 'post-28', 'user-6', 'I do this at least once a month. Now I just pretend I was stretching.', 13),
        ('c35', 'post-29', 'user-1', 'Oh no! What happened after? Did you survive??', 9),
        ('c36', 'post-31', 'user-3', 'Auntie this is the sweetest story! 💕 From paiseh to love!', 6),
        ('c37', 'post-31', 'user-1', 'From paiseh to 38 years married! This is relationship goals!', 5),
        
        # Boleh comments - post likes: 81, 63, 47, 35, 29
        ('c38', 'post-33', 'user-7', 'Makes me proud to be Singaporean! Our athletes work so hard.', 12),
        ('c39', 'post-33', 'user-2', 'We may be small but we have big hearts! Singapore boleh!', 9),
        ('c40', 'post-34', 'user-4', 'Our pioneers really built something special. We must continue their legacy.', 10),
        ('c41', 'post-34', 'user-1', 'Never take for granted what our founding fathers sacrificed for us.', 7),
        ('c42', 'post-37', 'user-3', 'Thank you Uncle for sharing. Your generation paved the way for us.', 4),
        
        # Lepak comments - post likes: 74, 59, 45, 38, 27, 19
        ('c43', 'post-38', 'user-2', 'East Coast satay is the best! The breeze also very shiok.', 11),
        ('c44', 'post-38', 'user-7', 'I also like East Coast. Good for morning walk and evening lepak.', 8),
        ('c45', 'post-39', 'user-5', 'Young people still know how to enjoy simple things. Good to see!', 9),
        ('c46', 'post-39', 'user-4', 'Mamak sessions are therapeutic. Best conversations happen at 2am.', 7),
        ('c47', 'post-41', 'user-1', 'Uncle, $8 coffee got aircon mah 😂 But void deck chess still the best!', 6),
        ('c48', 'post-41', 'user-3', 'Void deck chess is free! No need to pay anything. Smart!', 5)
    ]
    cursor.executemany(
        "INSERT INTO comments (id, post_id, user_id, text, likes_count) VALUES (?, ?, ?, ?, ?)",
        comments
    )
    
    polls = [
        ('poll-1', 'post-20', 'Which chicken rice is the BEST?'),
        ('poll-2', 'post-7', 'Best way to celebrate finishing exams?'),
        ('poll-3', 'post-33', 'What makes you most proud to be Singaporean?')
    ]
    cursor.executemany(
        "INSERT INTO polls (id, post_id, question) VALUES (?, ?, ?)",
        polls
    )
    
    poll_options = [
        ('opt-1a', 'poll-1', 'Tian Tian', 45),
        ('opt-1b', 'poll-1', 'Ah Tai', 38),
        ('opt-1c', 'poll-1', 'Boon Tong Kee', 22),
        ('opt-1d', 'poll-1', 'Other (comment below!)', 12),
        
        ('opt-2a', 'poll-2', 'Sleep for 12 hours straight', 67),
        ('opt-2b', 'poll-2', 'Makan session with friends', 54),
        ('opt-2c', 'poll-2', 'Netflix marathon', 41),
        ('opt-2d', 'poll-2', 'Go shopping/travel', 29),
        
        ('opt-3a', 'poll-3', 'Our food culture', 56),
        ('opt-3b', 'poll-3', 'Safety and cleanliness', 48),
        ('opt-3c', 'poll-3', 'Multiracial harmony', 62),
        ('opt-3d', 'poll-3', 'World-class infrastructure', 31)
    ]
    cursor.executemany(
        "INSERT INTO poll_options (id, poll_id, text, votes_count) VALUES (?, ?, ?, ?)",
        poll_options
    )
    
    conn.commit()