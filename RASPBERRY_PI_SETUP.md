# 🍓 Raspberry Pi Setup cho SMC Bot

## Hardware cần thiết:
- Raspberry Pi 4 (4GB RAM) - ~$75
- MicroSD 32GB Class 10 - ~$15  
- Power adapter - ~$10
- Total: ~$100 (one-time)

## Setup steps:

### 1. Flash Raspberry Pi OS
```bash
# Download Raspberry Pi Imager
# Flash "Raspberry Pi OS Lite" lên SD card
# Enable SSH trong config
```

### 2. SSH vào Pi và setup
```bash
ssh pi@<pi-ip-address>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install python3-pip python3-venv git -y
sudo apt install python3-dev python3-setuptools -y

# Install TA-Lib dependencies
sudo apt install build-essential wget -y
```

### 3. Clone bot code
```bash
git clone <repo> /home/pi/bot-trade
cd /home/pi/bot-trade

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Setup auto-start
```bash
# Thêm vào crontab
crontab -e

# Thêm dòng này:
@reboot cd /home/pi/bot-trade && ./venv/bin/python smc_bot.py
```

### 5. Monitoring
```bash
# Setup log file
echo "python smc_bot.py >> /home/pi/bot.log 2>&1" > run_bot.sh
chmod +x run_bot.sh

# Crontab:
@reboot /home/pi/bot-trade/run_bot.sh
```

## Ưu điểm:
- Chi phí 1 lần $100
- Tiêu thụ điện thấp (~5W)
- Chạy 24/7 tại nhà
- Full control

## Nhược điểm:  
- Phụ thuộc điện/mạng nhà
- Cần setup và maintain