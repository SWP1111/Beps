# BEPS Server

## Overview
The BEPS Server is a Node.js application designed to manage and serve video content securely. It includes user authentication and content management features.

## Project Structure
```
beps_server
├── config
│   └── config.js          # Configuration settings for the application
├── controllers
│   ├── authController.js  # Functions related to user authentication
│   └── contentController.js # Functions for handling content-related requests
├── middleware
│   └── authMiddleware.js   # Middleware for authenticating JWT tokens
├── routes
│   ├── authRoutes.js      # Routes related to authentication
│   └── contentRoutes.js    # Routes related to content management
├── utils
│   └── fileUtils.js       # Utility functions for file operations
├── server.js              # Entry point of the application
├── package.json           # npm configuration file
└── README.md              # Documentation for the project
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd beps_server
   ```
3. Install the dependencies:
   ```
   npm install
   ```

## Usage
1. Start the server:
   ```
   node server.js
   ```
2. Access the application at `http://localhost:3000`.

## API Endpoints
- **Authentication**
  - `POST /login`: Authenticate user and generate a JWT token.
  
- **Content Management**
  - `GET /list-directories`: List directories in the content storage.
  - `GET /view-details/*`: View details of specific files.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.