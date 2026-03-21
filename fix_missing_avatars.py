import sqlite3
import random
import os
from config import Config

def fix_avatars():
    db_path = Config.DATABASE
    
    # Try to connect, if it doesn't exist, we don't need to fix anything yet
    if not os.path.exists(db_path):
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    avatars = [
        'https://images.unsplash.com/photo-1531384441138-2736e62e0919?auto=format&fit=crop&q=80&w=300', # African man smiling
        'https://images.unsplash.com/photo-1506803682981-6e718a9dd3ee?auto=format&fit=crop&q=80&w=300', # African woman looking
        'https://images.unsplash.com/photo-1523824922871-2292f3cbdb05?auto=format&fit=crop&q=80&w=300', # African student
        'https://images.unsplash.com/photo-1544928147-79a2dbc1f389?auto=format&fit=crop&q=80&w=300', # African tech worker
        'https://images.unsplash.com/photo-1580894732444-8ecded7900cd?auto=format&fit=crop&q=80&w=300', # African woman studying
        'https://images.unsplash.com/photo-1504275107785-981de7673fa1?auto=format&fit=crop&q=80&w=300', # African youth
        'https://images.unsplash.com/photo-1531123414708-20ddcb1e3ce1?auto=format&fit=crop&q=80&w=300', # African young man
        'https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&q=80&w=300', # African server admin
    ]
    
    # Get all users with empty or null profile pics
    cursor.execute('SELECT id FROM users WHERE profile_pic_url IS NULL OR profile_pic_url = ""')
    users = cursor.fetchall()
    
    for user_id in users:
        pic = random.choice(avatars)
        cursor.execute('UPDATE users SET profile_pic_url = ? WHERE id = ?', (pic, user_id[0]))
        
    conn.commit()
    conn.close()
    print(f"Updated {len(users)} users with African profile pictures!")

if __name__ == '__main__':
    fix_avatars()
