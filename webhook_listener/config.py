import os

# Path to your Git repository on the VM
# Replace this with the absolute path to your repository
REPO_PATH = '/path/to/your/repo'

# Secret token for webhook verification
# Replace this with your actual secret token
SECRET_TOKEN = 'your_github_webhook_secret'

# The port on which the webhook listener will run
PORT = 5000

# Whether to run the app in debug mode (False for production)
DEBUG = False 