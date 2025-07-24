# Ngrok Setup for Development

## Overview
When developing locally, you need a public URL for SignalWire to send webhook events. Ngrok provides a secure tunnel to your local development environment.

## Installation

### macOS
```bash
brew install ngrok/ngrok/ngrok
```

### Linux
```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

### Windows
Download from https://ngrok.com/download

## Configuration

1. **Sign up** at https://ngrok.com
2. **Get your authtoken** from the dashboard
3. **Configure ngrok**:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

## Usage with LiveCall

1. **Start LiveCall services**:
   ```bash
   make dev
   ```

2. **In a separate terminal, start ngrok**:
   ```bash
   ngrok http 3030
   ```

3. **Note your ngrok URL** (e.g., `https://abc123.ngrok-free.app`)

4. **Update your .env file**:
   ```env
   PUBLIC_URL=https://abc123.ngrok-free.app
   ```

5. **Configure SignalWire webhook URL**:
   - Go to your SignalWire dashboard
   - Set webhook URL to: `https://abc123.ngrok-free.app/webhooks/signalwire/transcribe`

## Tips

- **Free tier limitations**: URL changes on restart, limited requests/minute
- **Paid features**: Custom domains, higher limits
- **Security**: Ngrok URLs are public - use webhook validation
- **Debugging**: Visit http://localhost:4040 for ngrok inspector

## Alternative Solutions

- **Cloudflare Tunnel**: Free alternative with permanent URLs
- **Tailscale Funnel**: Good for team development
- **localtunnel**: Simple open-source option

## Production

In production, ngrok is not needed. Use your actual domain with proper SSL certificates.