#!/bin/bash

# Carlos Trading Bot - Ubuntu Service Setup Script
# This script creates a systemd service for the Carlos Trading Bot

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service configuration
SERVICE_NAME="carlos-trading-bot"
SERVICE_USER="carlos-bot"
INSTALL_DIR="/opt/carlos-trading-bot"
LOG_DIR="/var/log/carlos-trading-bot"
CONFIG_DIR="/etc/carlos-trading-bot"

echo -e "${BLUE}🤖 Carlos Trading Bot - Ubuntu Service Setup${NC}"
echo -e "${BLUE}===============================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run this script as root (use sudo)${NC}"
    exit 1
fi

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the correct directory
if [ ! -f "main.py" ] || [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the carlos_tg_bot directory"
    exit 1
fi

echo -e "${BLUE}📋 Setup Information:${NC}"
echo "Service Name: $SERVICE_NAME"
echo "Service User: $SERVICE_USER"
echo "Install Directory: $INSTALL_DIR"
echo "Log Directory: $LOG_DIR"
echo "Config Directory: $CONFIG_DIR"
echo ""

read -p "Continue with installation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo -e "${BLUE}🔧 Starting installation...${NC}"

# 1. Update system packages
echo -e "${BLUE}📦 Updating system packages...${NC}"
apt update

# 2. Install required system packages
echo -e "${BLUE}📦 Installing system dependencies...${NC}"
apt install -y python3 python3-pip python3-venv sqlite3 curl wget

# 3. Create service user
echo -e "${BLUE}👤 Creating service user...${NC}"
if id "$SERVICE_USER" &>/dev/null; then
    print_warning "User $SERVICE_USER already exists"
else
    useradd --system --shell /bin/bash --home-dir $INSTALL_DIR --create-home $SERVICE_USER
    print_status "Created user $SERVICE_USER"
fi

# 4. Create directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p $INSTALL_DIR
mkdir -p $LOG_DIR
mkdir -p $CONFIG_DIR
mkdir -p $INSTALL_DIR/data
mkdir -p $INSTALL_DIR/logs
mkdir -p $INSTALL_DIR/backups

# 5. Copy application files
echo -e "${BLUE}📋 Copying application files...${NC}"
cp -r . $INSTALL_DIR/
print_status "Application files copied"

# 6. Set up Python virtual environment
echo -e "${BLUE}🐍 Setting up Python virtual environment...${NC}"
cd $INSTALL_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_status "Python virtual environment created and dependencies installed"

# 7. Create environment file template
echo -e "${BLUE}⚙️ Creating environment configuration...${NC}"
if [ ! -f "$CONFIG_DIR/.env" ]; then
    cp env.example $CONFIG_DIR/.env
    print_warning "Environment file created at $CONFIG_DIR/.env"
    print_warning "Please edit this file with your actual credentials!"
else
    print_warning "Environment file already exists at $CONFIG_DIR/.env"
fi

# Create symlink to config
ln -sf $CONFIG_DIR/.env $INSTALL_DIR/.env

# 8. Create systemd service file
echo -e "${BLUE}🔧 Creating systemd service file...${NC}"
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Carlos Trading Bot - Telegram Cryptocurrency Trading Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python main.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR $LOG_DIR $CONFIG_DIR
CapabilityBoundingSet=
AmbientCapabilities=

# Resource limits
LimitNOFILE=65536
MemoryMax=512M

[Install]
WantedBy=multi-user.target
EOF

print_status "Systemd service file created"

# 9. Create log rotation configuration
echo -e "${BLUE}📝 Setting up log rotation...${NC}"
cat > /etc/logrotate.d/$SERVICE_NAME << EOF
$LOG_DIR/*.log $INSTALL_DIR/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        systemctl reload $SERVICE_NAME > /dev/null 2>&1 || true
    endscript
}
EOF

print_status "Log rotation configured"

# 10. Set correct permissions
echo -e "${BLUE}🔐 Setting file permissions...${NC}"
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
chown -R $SERVICE_USER:$SERVICE_USER $LOG_DIR
chown -R $SERVICE_USER:$SERVICE_USER $CONFIG_DIR
chmod 755 $INSTALL_DIR
chmod 755 $LOG_DIR
chmod 750 $CONFIG_DIR
chmod 600 $CONFIG_DIR/.env
print_status "File permissions set"

# 11. Create management scripts
echo -e "${BLUE}📜 Creating management scripts...${NC}"

# Create start script
cat > $INSTALL_DIR/start.sh << 'EOF'
#!/bin/bash
systemctl start carlos-trading-bot
systemctl status carlos-trading-bot --no-pager
EOF

# Create stop script
cat > $INSTALL_DIR/stop.sh << 'EOF'
#!/bin/bash
systemctl stop carlos-trading-bot
systemctl status carlos-trading-bot --no-pager
EOF

# Create status script
cat > $INSTALL_DIR/status.sh << 'EOF'
#!/bin/bash
echo "=== Service Status ==="
systemctl status carlos-trading-bot --no-pager
echo ""
echo "=== Recent Logs ==="
journalctl -u carlos-trading-bot --no-pager -n 20
EOF

# Create logs script
cat > $INSTALL_DIR/logs.sh << 'EOF'
#!/bin/bash
echo "=== Live Logs (Ctrl+C to exit) ==="
journalctl -u carlos-trading-bot -f
EOF

# Create update script
cat > $INSTALL_DIR/update.sh << 'EOF'
#!/bin/bash
echo "🔄 Updating Carlos Trading Bot..."
systemctl stop carlos-trading-bot
cd /opt/carlos-trading-bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
systemctl start carlos-trading-bot
echo "✅ Update completed!"
systemctl status carlos-trading-bot --no-pager
EOF

chmod +x $INSTALL_DIR/*.sh
print_status "Management scripts created"

# 12. Enable and start service
echo -e "${BLUE}🚀 Enabling and starting service...${NC}"
systemctl daemon-reload
systemctl enable $SERVICE_NAME

print_status "Service enabled"

# 13. Create firewall rules (if ufw is installed)
if command -v ufw &> /dev/null; then
    echo -e "${BLUE}🔥 Configuring firewall...${NC}"
    # Allow SSH
    ufw allow ssh
    # Allow outbound HTTPS for API calls
    ufw allow out 443
    # Allow outbound HTTP for updates
    ufw allow out 80
    print_status "Firewall rules configured"
fi

echo -e "${GREEN}🎉 Installation completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Edit the configuration file:"
echo "   sudo nano $CONFIG_DIR/.env"
echo ""
echo "2. Add your credentials:"
echo "   - TELEGRAM_BOT_TOKEN"
echo "   - TELEGRAM_CHAT_ID"
echo "   - TELEGRAM_AUTHORIZED_USERS"
echo "   - CRYPTO_API_KEY"
echo "   - CRYPTO_API_SECRET"
echo ""
echo "3. Start the service:"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo -e "${BLUE}🛠️ Management Commands:${NC}"
echo "Start service:     sudo systemctl start $SERVICE_NAME"
echo "Stop service:      sudo systemctl stop $SERVICE_NAME"
echo "Restart service:   sudo systemctl restart $SERVICE_NAME"
echo "Service status:    sudo systemctl status $SERVICE_NAME"
echo "View logs:         sudo journalctl -u $SERVICE_NAME -f"
echo "Enable at boot:    sudo systemctl enable $SERVICE_NAME"
echo "Disable at boot:   sudo systemctl disable $SERVICE_NAME"
echo ""
echo -e "${BLUE}📜 Quick Scripts (in $INSTALL_DIR):${NC}"
echo "./start.sh         - Start service and show status"
echo "./stop.sh          - Stop service and show status"
echo "./status.sh        - Show service status and recent logs"
echo "./logs.sh          - View live logs"
echo "./update.sh        - Update bot from git and restart"
echo ""
echo -e "${YELLOW}⚠️  Important:${NC}"
echo "- Edit $CONFIG_DIR/.env with your actual credentials"
echo "- Service runs as user '$SERVICE_USER' for security"
echo "- Logs are available via journalctl or in $LOG_DIR"
echo "- Service will auto-restart on failure"
echo "- Service will start automatically on boot"
echo ""
echo -e "${GREEN}✅ Carlos Trading Bot service installation complete!${NC}"
