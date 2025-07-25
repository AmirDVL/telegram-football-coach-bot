"""
Test script for Football Coach Telegram Bot
This script validates the bot configuration and dependencies
"""

import sys
import os
import importlib.util

def test_dependencies():
    """Test if all required dependencies are installed"""
    print("🔍 Testing dependencies...")
    
    required_packages = [
        'telegram',
        'python_telegram_bot', 
        'dotenv',
        'aiofiles',
        'asyncio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'python_telegram_bot':
                import telegram
                print(f"   ✅ {package} - OK")
            elif package == 'dotenv':
                from dotenv import load_dotenv
                print(f"   ✅ {package} - OK")
            elif package == 'aiofiles':
                import aiofiles
                print(f"   ✅ {package} - OK")
            elif package == 'asyncio':
                import asyncio
                print(f"   ✅ {package} - OK")
            else:
                spec = importlib.util.find_spec(package)
                if spec is None:
                    missing_packages.append(package)
                    print(f"   ❌ {package} - MISSING")
                else:
                    print(f"   ✅ {package} - OK")
        except ImportError:
            missing_packages.append(package)
            print(f"   ❌ {package} - MISSING")
    
    return missing_packages

def test_config_files():
    """Test if configuration files exist"""
    print("\n📁 Testing configuration files...")
    
    files_to_check = [
        ('main.py', 'Main bot file'),
        ('config.py', 'Configuration file'),
        ('data_manager.py', 'Data manager file'),
        ('requirements.txt', 'Requirements file'),
        ('.env', 'Environment file (you need to create this)')
    ]
    
    missing_files = []
    
    for filename, description in files_to_check:
        if os.path.exists(filename):
            print(f"   ✅ {filename} - {description}")
        else:
            missing_files.append(filename)
            if filename == '.env':
                print(f"   ⚠️  {filename} - {description}")
            else:
                print(f"   ❌ {filename} - {description}")
    
    return missing_files

def test_env_variables():
    """Test environment variables"""
    print("\n🔐 Testing environment variables...")
    
    if not os.path.exists('.env'):
        print("   ⚠️  .env file not found")
        print("   📝 Create .env file with:")
        print("      BOT_TOKEN=your_bot_token_here")
        print("      ADMIN_ID=your_admin_chat_id_here")
        return False
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        bot_token = os.getenv('BOT_TOKEN')
        admin_id = os.getenv('ADMIN_ID')
        
        if bot_token:
            print(f"   ✅ BOT_TOKEN - Found ({'*' * 10}{bot_token[-10:] if len(bot_token) > 10 else bot_token})")
        else:
            print("   ❌ BOT_TOKEN - Missing")
            
        if admin_id:
            print(f"   ✅ ADMIN_ID - Found ({admin_id})")
        else:
            print("   ⚠️  ADMIN_ID - Missing (optional)")
            
        return bool(bot_token)
        
    except Exception as e:
        print(f"   ❌ Error loading .env file: {e}")
        return False

def test_imports():
    """Test if main modules can be imported"""
    print("\n📦 Testing module imports...")
    
    modules_to_test = [
        ('config', 'Configuration module'),
        ('data_manager', 'Data manager module')
    ]
    
    import_errors = []
    
    for module_name, description in modules_to_test:
        try:
            if module_name == 'config':
                from config import Config
                print(f"   ✅ {module_name} - {description}")
            elif module_name == 'data_manager':
                from data_manager import DataManager
                print(f"   ✅ {module_name} - {description}")
        except ImportError as e:
            import_errors.append((module_name, str(e)))
            print(f"   ❌ {module_name} - Error: {e}")
        except Exception as e:
            import_errors.append((module_name, str(e)))
            print(f"   ❌ {module_name} - Error: {e}")
    
    return import_errors

def main():
    """Main test function"""
    print("🤖 Football Coach Telegram Bot - Configuration Test")
    print("=" * 50)
    
    # Test dependencies
    missing_deps = test_dependencies()
    
    # Test config files
    missing_files = test_config_files()
    
    # Test environment variables
    env_ok = test_env_variables()
    
    # Test imports
    import_errors = test_imports()
    
    # Summary
    print("\n📊 Test Summary:")
    print("=" * 30)
    
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("   Run: pip install -r requirements.txt")
    else:
        print("✅ All dependencies installed")
    
    if missing_files and '.env' not in missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
    elif '.env' in missing_files:
        print("⚠️  .env file needs to be created")
    else:
        print("✅ All required files present")
    
    if not env_ok:
        print("❌ Environment configuration incomplete")
    else:
        print("✅ Environment configuration OK")
    
    if import_errors:
        print(f"❌ Import errors: {len(import_errors)}")
        for module, error in import_errors:
            print(f"   - {module}: {error}")
    else:
        print("✅ All modules import successfully")
    
    # Final recommendation
    print("\n🎯 Next Steps:")
    if missing_deps:
        print("1. Install dependencies: pip install -r requirements.txt")
    if not env_ok:
        print("2. Create .env file with your bot token")
        print("3. Get bot token from @BotFather on Telegram")
    if not missing_deps and env_ok and not import_errors:
        print("✅ Ready to run! Execute: python main.py")
    
    print("\n💡 Need help? Check README.md for detailed instructions")

if __name__ == "__main__":
    main()
