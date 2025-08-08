"""
Bot Startup Validation Report
"""

print("🤖 Football Coach Bot - Startup Validation")
print("=" * 50)

# Test 1: Syntax Check
print("\n📋 Test 1: Syntax Validation")
try:
    import py_compile
    py_compile.compile('main.py', doraise=True)
    print("✅ main.py syntax is VALID")
    syntax_ok = True
except Exception as e:
    print(f"❌ Syntax error: {e}")
    syntax_ok = False

# Test 2: Import Check
print("\n📋 Test 2: Import Validation")
try:
    import main
    print("✅ main.py imports successfully")
    import_ok = True
except Exception as e:
    print(f"❌ Import error: {e}")
    import_ok = False

# Test 3: Configuration Check
print("\n📋 Test 3: Configuration Validation")
try:
    from config import Config
    print(f"✅ BOT_TOKEN configured: {bool(Config.BOT_TOKEN)}")
    print(f"✅ ADMIN_ID configured: {Config.ADMIN_ID}")
    print(f"✅ USE_DATABASE: {Config.USE_DATABASE}")
    config_ok = True
except Exception as e:
    print(f"❌ Config error: {e}")
    config_ok = False

# Test 4: Dependencies Check
print("\n📋 Test 4: Dependencies Validation")
try:
    import telegram
    from telegram.ext import Application
    import asyncpg
    import aiofiles
    from PIL import Image
    print("✅ All required packages available")
    deps_ok = True
except Exception as e:
    print(f"❌ Dependency error: {e}")
    deps_ok = False

# Summary
print("\n" + "=" * 50)
print("📊 VALIDATION SUMMARY:")
print(f"   Syntax:        {'✅ PASS' if syntax_ok else '❌ FAIL'}")
print(f"   Imports:       {'✅ PASS' if import_ok else '❌ FAIL'}")
print(f"   Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
print(f"   Dependencies:  {'✅ PASS' if deps_ok else '❌ FAIL'}")

all_ok = syntax_ok and import_ok and config_ok and deps_ok

if all_ok:
    print("\n🎉 ALL TESTS PASSED!")
    print("🚀 Bot is ready to run with: python main.py")
else:
    print("\n❌ Some tests failed. Fix the issues above before running the bot.")

print("\nValidation complete.")
