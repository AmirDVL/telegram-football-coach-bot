#!/bin/bash

echo "🚀 Installing Football Coach Telegram Bot..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

# Check if PostgreSQL is available (optional for local development)
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL found - Database mode available"
    POSTGRES_AVAILABLE=true
else
    echo "⚠️  PostgreSQL not found - Will use JSON file mode"
    POSTGRES_AVAILABLE=false
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Setup environment file
if [ ! -f .env ]; then
    echo ""
    echo "⚙️  Creating environment configuration..."
    
    # Get bot credentials
    read -p "Enter your Bot Token (from @BotFather): " BOT_TOKEN
    read -p "Enter your Telegram User ID (Admin ID): " ADMIN_ID
    
    if [ "$POSTGRES_AVAILABLE" = true ]; then
        echo ""
        echo "Choose storage mode:"
        echo "1) PostgreSQL Database (Recommended for production)"
        echo "2) JSON Files (Simple setup for development)"
        read -p "Enter choice [1-2]: " STORAGE_CHOICE
        
        if [ "$STORAGE_CHOICE" = "1" ]; then
            echo "📊 Setting up PostgreSQL configuration..."
            read -p "Database Host [localhost]: " DB_HOST
            DB_HOST=${DB_HOST:-localhost}
            read -p "Database Port [5432]: " DB_PORT
            DB_PORT=${DB_PORT:-5432}
            read -p "Database Name [football_coach_bot]: " DB_NAME
            DB_NAME=${DB_NAME:-football_coach_bot}
            read -p "Database User [footballbot]: " DB_USER
            DB_USER=${DB_USER:-footballbot}
            read -s -p "Database Password: " DB_PASSWORD
            echo ""
            
            cat > .env << EOF
# 🤖 Telegram Bot Configuration
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID

# 🗄️ Database Configuration (PostgreSQL)
USE_DATABASE=true
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# 🛡️ Production Settings
DEBUG=false
EOF
        else
            cat > .env << EOF
# 🤖 Telegram Bot Configuration
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID

# 🗄️ Database Configuration
USE_DATABASE=false

# 🛡️ Development Settings
DEBUG=true
EOF
        fi
    else
        cat > .env << EOF
# 🤖 Telegram Bot Configuration
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID

# 🗄️ Database Configuration (JSON Files)
USE_DATABASE=false

# 🛡️ Development Settings
DEBUG=true
EOF
    fi
    
    # Set secure permissions
    chmod 600 .env
    echo "✅ Environment file created with secure permissions"
else
    echo "✅ Environment file already exists"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "📋 Next steps:"
if grep -q "USE_DATABASE=true" .env 2>/dev/null; then
    echo "1. 🗄️  Set up PostgreSQL database (if not done already)"
    echo "2. ▶️  Run: python main.py"
    echo ""
    echo "🔧 Database setup commands:"
    echo "   sudo -u postgres createdb football_coach_bot"
    echo "   sudo -u postgres createuser footballbot"
    echo "   sudo -u postgres psql -c \"ALTER USER footballbot WITH ENCRYPTED PASSWORD 'your_password';\""
    echo "   sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE football_coach_bot TO footballbot;\""
else
    echo "1. ▶️  Run: python main.py"
    echo ""
    echo "💡 To enable PostgreSQL later:"
    echo "   - Install PostgreSQL"
    echo "   - Update .env file: USE_DATABASE=true"
    echo "   - Add database credentials to .env"
fi
echo ""
