import sqlite3
import os

def summarize_database(db_path='scores-backup-22feb26.db'):
    """
    Summarize database info and handle duplicate users by keeping first occurrence
    """
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"DATABASE SUMMARY: {db_path}")
        print("=" * 50)
        
        # Total entries
        cursor.execute("SELECT COUNT(*) FROM scores")
        total_entries = cursor.fetchone()[0]
        
        # Total unique users (by user_id)
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM scores")
        unique_users_by_id = cursor.fetchone()[0]
        
        # Total unique users (by username)
        cursor.execute("SELECT COUNT(DISTINCT username) FROM scores")
        unique_users_by_name = cursor.fetchone()[0]
        
        # Total unique games
        cursor.execute("SELECT COUNT(DISTINCT game) FROM scores")
        unique_games = cursor.fetchone()[0]
        
        # First occurrence of each user (by username)
        cursor.execute("""
            SELECT username, user_id, score, game, rowid
            FROM scores 
            WHERE rowid IN (
                SELECT MIN(rowid) 
                FROM scores 
                GROUP BY username
            )
            ORDER BY username
        """)
        first_occurrences = cursor.fetchall()
        
        # Find duplicate usernames
        cursor.execute("""
            SELECT username, COUNT(*) as count
            FROM scores 
            GROUP BY username 
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        duplicate_usernames = cursor.fetchall()
        
        # Games list
        cursor.execute("SELECT DISTINCT game FROM scores ORDER BY game")
        games_list = [row[0] for row in cursor.fetchall()]
        
        # Display summary
        print(f"Total entries in database: {total_entries}")
        print(f"Unique users (by user_id): {unique_users_by_id}")
        print(f"Unique users (by username): {unique_users_by_name}")
        print(f"Total unique games: {unique_games}")
        print(f"First occurrences kept: {len(first_occurrences)}")
        print()
        
        print("GAMES IN DATABASE:")
        for i, game in enumerate(games_list, 1):
            print(f"  {i}. {game}")
        print()
        
        if duplicate_usernames:
            print("DUPLICATE USERNAMES FOUND:")
            for username, count in duplicate_usernames:
                print(f"  {username}: {count} entries")
            print()
        
        print("FIRST OCCURRENCE OF EACH USER:")
        print("Username | User_ID | Score | Game")
        print("-" * 40)
        for username, user_id, score, game, rowid in first_occurrences:
            print(f"{username:<12} | {user_id:<7} | {score:<5} | {game}")
        
        print(f"\nTotal unique users processed: {len(first_occurrences)}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

def create_unique_users_table(db_path='unique.db'):
    """
    Create a new table with only first occurrence of each user
    """
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create new table for unique users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unique_users (
                user_id INTEGER,
                username TEXT,
                score INTEGER,
                game TEXT,
                original_rowid INTEGER,
                PRIMARY KEY (username)
            )
        ''')
        
        # Clear existing data
        cursor.execute("DELETE FROM unique_users")
        
        # Insert first occurrence of each user
        cursor.execute('''
            INSERT INTO unique_users (user_id, username, score, game, original_rowid)
            SELECT user_id, username, score, game, rowid
            FROM scores 
            WHERE rowid IN (
                SELECT MIN(rowid) 
                FROM scores 
                GROUP BY username
            )
        ''')
        
        conn.commit()
        
        # Count inserted records
        cursor.execute("SELECT COUNT(*) FROM unique_users")
        unique_count = cursor.fetchone()[0]
        
        print(f"Created 'unique_users' table with {unique_count} unique users")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def main():
    """Main function"""
    
    print("Choose an option:")
    print("1. Show database summary")
    print("2. Create unique users table")
    print("3. Both")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        summarize_database()
    elif choice == "2":
        create_unique_users_table()
    elif choice == "3":
        summarize_database()
        print("\n" + "="*50 + "\n")
        create_unique_users_table()
    else:
        print("Invalid choice. Showing summary...")
        summarize_database()

if __name__ == "__main__":
    main()