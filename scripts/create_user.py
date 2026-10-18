import sys
import argparse
import httpx
from app.config import get_settings

settings = get_settings()

def create_admin_user(email: str, password: str, full_name: str = "Admin User"):
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "full_name": full_name
        }
    }
    
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, headers=headers, json=payload)
        if response.status_code in (200, 201):
            user_data = response.json()
            print(f"SUCCESS: User '{email}' created and auto-confirmed!")
            print(f"User ID: {user_data.get('id')}")
            return user_data
        else:
            print(f"ERROR ({response.status_code}): {response.text}")
            return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create a Supabase user bypassing email rate limits")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="User password")
    parser.add_argument("--name", default="Admin User", help="User full name")
    args = parser.parse_args()
    create_admin_user(args.email, args.password, args.name)
