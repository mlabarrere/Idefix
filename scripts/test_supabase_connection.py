#!/usr/bin/env python3
"""Test Supabase connection and schema."""
import asyncio
import asyncpg
from dotenv import load_dotenv
import os
import sys

load_dotenv()

async def main():
    url = os.getenv('DATABASE_URL')
    if not url:
        print("✗ DATABASE_URL not set in .env")
        return 1
    
    if '[DB_PASSWORD]' in url:
        print("✗ DATABASE_URL still contains [DB_PASSWORD] placeholder")
        print("  Get password from: https://supabase.com/dashboard/project/peeswtivgkjkmlhtvnau/settings/database")
        return 1
    
    # asyncpg needs url without +asyncpg suffix
    url = url.replace('+asyncpg', '')
    
    try:
        print("Connecting to Supabase...")
        conn = await asyncpg.connect(url, timeout=10)
        
        # Check version
        version = await conn.fetchval('SELECT version()')
        print(f"\n✓ Connected to Supabase PostgreSQL")
        print(f"  Version: {version[:80]}...")
        
        # Check schema
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        table_names = [t['tablename'] for t in tables]
        
        expected = ['channels', 'channel_scores', 'comments', 'edges', 
                   'episodes', 'evidence_dossiers', 'messages', 'scores_run_meta']
        
        print(f"\n  Tables found: {len(table_names)}")
        for name in table_names:
            status = "✓" if name in expected else "?"
            print(f"    {status} {name}")
        
        missing = set(expected) - set(table_names)
        if missing:
            print(f"\n  ⚠ Missing tables: {missing}")
            print("  Run migration: supabase db push")
            print("  Or via SQL Editor: https://supabase.com/dashboard/project/peeswtivgkjkmlhtvnau/sql/new")
        
        # Check data
        counts = {}
        for table in ['channels', 'messages', 'edges']:
            if table in table_names:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM {table}')
                counts[table] = count
        
        print(f"\n  Row counts:")
        for table, count in counts.items():
            print(f"    {table}: {count:,}")
        
        await conn.close()
        print("\n✓ All checks passed")
        return 0
        
    except asyncpg.InvalidPasswordError:
        print("\n✗ Invalid password")
        print("  Check DATABASE_URL password in .env")
        return 1
    except asyncpg.InvalidAuthorizationSpecificationError:
        print("\n✗ Authentication failed")
        print("  Check DATABASE_URL credentials in .env")
        return 1
    except asyncpg.PostgresError as e:
        print(f"\n✗ PostgreSQL error: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
