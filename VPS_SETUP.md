# 🌐 Hướng dẫn deploy bot lên VPS

## 1. Setup VPS Ubuntu 20.04+

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python và pip
sudo apt install python3 python3-pip python3-venv git -y

# Install dependencies cần thiết
sudo apt install build-essential libssl-dev libffi-dev python3-dev -y
```

## 2. Clone và setup bot

```bash
# Clone code từ git hoặc upload files
git clone <your-repo> bot-trade
# Hoặc scp files từ máy local:
# scp -r /Users/chiennd/bot-trade user@server:/home/user/

cd bot-trade

# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install python-dotenv pybit pandas numpy matplotlib plotly TA-Lib
```

## 3. Setup file .env

```bash
nano .env
# Copy nội dung .env từ máy local
```

## 4. Test bot trước

```bash
python smc_bot.py  # Test 1 lần
```

## 5. Chạy 24/7 với systemd (Auto restart)

```bash
# Tạo service file
sudo nano /etc/systemd/system/smc-bot.service
```

Nội dung file service:
```ini
[Unit]
Description=SMC Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bot-trade
Environment=PATH=/home/ubuntu/bot-trade/venv/bin
ExecStart=/home/ubuntu/bot-trade/venv/bin/python /home/ubuntu/bot-trade/smc_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# Enable và start service
sudo systemctl daemon-reload
sudo systemctl enable smc-bot
sudo systemctl start smc-bot

# Check status
sudo systemctl status smc-bot

# Xem logs
sudo journalctl -u smc-bot -f
```

## 6. Alternative: Screen/Tmux (Đơn giản hơn)

```bash
# Install screen
sudo apt install screen -y

# Chạy bot trong screen session
screen -S smc-bot
cd bot-trade
source venv/bin/activate
python smc_bot.py

# Detach: Ctrl+A, D
# Reattach: screen -r smc-bot
# List sessions: screen -ls
```

## 7. Monitoring và Alerts

```bash
# Setup log rotation
sudo nano /etc/logrotate.d/smc-bot

# Nội dung:
/var/log/smc-bot.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
}
```

## 8. Security

```bash
# Setup firewall (chỉ SSH)
sudo ufw enable
sudo ufw allow ssh

# Đổi SSH port (optional)
sudo nano /etc/ssh/sshd_config
# Port 2222

# Tắt password auth, chỉ dùng SSH key
# PasswordAuthentication no
```

## Chi phí ước tính:
- VPS $5/tháng = $60/năm
- Chạy 24/7 không lo mất điện, mất mạng
- Performance ổn định hơn máy cá nhân