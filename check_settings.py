#!/usr/bin/env python
"""Quick script to check settings in database"""
from app import create_app
from app.models.app_settings import AppSetting

app = create_app()
with app.app_context():
    settings = AppSetting.query.all()

    print("=== ALL SETTINGS ===")
    print(f"Total: {len(settings)}")
    print()

    # Group by user_id
    global_settings = [s for s in settings if s.user_id is None]
    user_settings = [s for s in settings if s.user_id is not None]

    print(f"GLOBAL SETTINGS (user_id=None): {len(global_settings)}")
    for s in global_settings:
        print(f"  {s.category:12s} | {s.setting_key:35s} = {s.setting_value}")

    print()
    print(f"USER-SPECIFIC SETTINGS: {len(user_settings)}")
    for s in user_settings:
        print(f"  User {s.user_id} | {s.category:12s} | {s.setting_key:35s} = {s.setting_value}")
