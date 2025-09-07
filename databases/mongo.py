from pymongo import MongoClient
from datetime import datetime
import bcrypt


def main():

    client = MongoClient("mongodb://localhost:27017/")
    db = client["admin"]
    users_collection = db["Roles_Access"]
    
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    try:
        users_collection.create_index("username", unique=True)
        print("✅ Unique index created on username")
    except:
        print("⚠️ Index already exists or error occurred")
    
    users_data = [
        {"username": "admin", "password": "admin123", "role": "admin"},
        {"username": "john_doe", "password": "password123", "role": "user"},
        {"username": "jane_smith", "password": "securepass", "role": "user"},
        {"username": "sahil", "password": "securepass", "role": "admin"}
    ]
    
    for user_data in users_data:
        try:
            user_document = {
                "username": user_data["username"],
                "password": hash_password(user_data["password"]),
                "role": user_data["role"],
                "created_at": datetime.utcnow(),
                "is_active": True
            }
            
            result = users_collection.insert_one(user_document)
            print(f"✅ User '{user_data['username']}' inserted: {result.inserted_id}")
            
        except Exception as e:
            print(f"❌ Error inserting {user_data['username']}: {e}")
    
    # Verify insertion
    print(f"\nTotal users in database: {users_collection.count_documents({})}")

if __name__ == "__main__":
    main()