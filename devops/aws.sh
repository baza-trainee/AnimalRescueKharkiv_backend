#!/bin/bash
# Update and install necessary packages
yum update -y
yum install -y git docker
sudo usermod -aG docker ec2-user

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Create a systemd service to run the desired script on startup
cat << 'EOF' > /etc/systemd/system/ark.service
[Unit]
Description=Run ARK Docker Compose on startup
After=network.target docker.service
Requires=docker.service

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/ARK
ExecStartPre=/usr/bin/docker-compose -f compose.yaml --profile backend down
ExecStartPre=/usr/bin/git pull
ExecStartPre=/usr/bin/docker-compose -f compose.yaml --profile backend build
ExecStart=/usr/bin/docker-compose -f compose.yaml --profile backend up -d
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the custom systemd service
sudo systemctl enable ark.service
sudo systemctl start ark.service
