import os
from supabase import create_client

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)

def get_secret(name: str) -> str:
    result = supabase.table("eyoungworks_vault") \
        .select("value") \
        .eq("name", name) \
        .single() \
        .execute()
    if not result.data:
        raise Exception(f"Vault: could not find secret '{name}'")
    return result.data["value"]

def get_system_secrets(system: str) -> dict:
    result = supabase.table("eyoungworks_vault") \
        .select("name, value") \
        .eq("system", system) \
        .execute()
    if not result.data:
        raise Exception(f"Vault: no secrets found for system '{system}'")
    return {row["name"]: row["value"] for row in result.data}