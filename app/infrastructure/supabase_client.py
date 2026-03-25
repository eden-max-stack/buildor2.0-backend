from supabase import create_client, Client
import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent.parent / ".env.dev"
load_dotenv(dotenv_path=env_path)

supabase_url: str = os.getenv("SUPABASE_URL")
# Change this:
# supabase_key: str = os.getenv("SUPABASE_ANON_KEY")

# To this:
supabase_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_key:
    raise ValueError("Missing SUPABASE_SERVICE_ROLE_KEY in .env.dev")

supabase: Client = create_client(supabase_url, supabase_key)