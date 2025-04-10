# GitHub Webhook Listener

A Flask application that listens for GitHub webhooks and automatically pulls the latest changes from a Git repository when a push event is received.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install flask requests
```

### 2. Configuration

Edit the `config.py` file and update the following settings:

- `REPO_PATH`: The absolute path to your Git repository on the VM.
- `SECRET_TOKEN`: A secret token that will be used to verify webhook requests from GitHub.
- `PORT`: The port on which the webhook listener will run (default: 5000).
- `DEBUG`: Whether to run in debug mode (set to `False` for production).

### 3. Setup as a Systemd Service (on Ubuntu VM)

1. Copy the webhook listener files to your Ubuntu VM:
   ```bash
   scp -r webhook_listener user@your-vm-ip:/path/to/destination
   ```

2. Edit the `github-webhook.service` file to set the correct paths and username:
   ```bash
   vim /path/to/webhook_listener/github-webhook.service
   ```
   - Update the `User` field with the appropriate username on your VM.
   - Update the `WorkingDirectory` to the absolute path of the webhook_listener directory.

3. Copy the service file to systemd:
   ```bash
   sudo cp /path/to/webhook_listener/github-webhook.service /etc/systemd/system/
   ```

4. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable github-webhook.service
   sudo systemctl start github-webhook.service
   ```

5. Check if the service is running:
   ```bash
   sudo systemctl status github-webhook.service
   ```

### 4. Firewall Configuration

Make sure the port (default: 5000) is open on your VM:

```bash
sudo ufw allow 5000/tcp
```

### 5. Configure GitHub Webhook

1. Go to your GitHub repository.
2. Click on **Settings** > **Webhooks** > **Add webhook**.
3. Set the following:
   - **Payload URL**: `http://your-vm-ip:5000/webhook`
   - **Content type**: `application/json`
   - **Secret**: The same secret token you set in the `config.py` file.
   - **Events**: Select "Just the push event".
4. Click **Add webhook**.

## Testing

To test if the webhook is working:

1. Make a small change to your repository and push it to GitHub.
2. Check the logs on your VM:
   ```bash
   sudo journalctl -u github-webhook.service -f
   ```
   or check the webhook.log file:
   ```bash
   tail -f /path/to/webhook_listener/webhook.log
   ```

3. Verify that the repository on your VM has been updated with the latest changes.

## Troubleshooting

If the webhook is not working:

1. Check the logs for any errors.
2. Verify that the webhook is configured correctly on GitHub.
3. Make sure the VM is accessible from the internet.
4. Check that the service is running on the VM.
5. Ensure the firewall is configured to allow traffic on the specified port. 
