from dotenv import load_dotenv
load_dotenv()

from school_app.config import get_config_class
from flask import Flask
from flask_migrate import Migrate
from school_app.extensions import db

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config_class())
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from school_app import models
    return app


# $env:FLASK_APP = "run.py"
# flask --app run.py db init

# <link rel="stylesheet" href="{{ url_for('static', filename='css/output.css') }}">

# $env:FLASK_APP = "run.py"
# flask shell

# // Define interfaces for your data structures
# interface ProfileData {
#     username?: string;
#     email?: string;
#     bio?: string;
#     [key: string]: any; // Allows additional properties if needed
# }

# interface ErrorResponse {
#     message: string;
# }

# interface SuccessResponse {
#     success: boolean;
#     data?: any;
#     [key: string]: any;
# }

# async function updateProfile(data: ProfileData): Promise<void> {
#     const token: string | null = localStorage.getItem('jwt_token'); // Or wherever you store it

#     try {
#         const response: Response = await fetch('/api/profile', {
#             method: 'PUT',
#             headers: {
#                 'Content-Type': 'application/json',
#                 'Authorization': `Bearer ${token}` // Passing the JWT
#             },
#             body: JSON.stringify(data)
#         });

#         // 1. Handle Authentication Failures (Redirect to Login)
#         if (response.status === 401) {
#             console.warn("Session expired. Booting to login...");
#             localStorage.removeItem('jwt_token'); // Clean up
#             window.location.href = '/login';      // JS handles the redirect!
#             return;
#         }

#         // 2. Handle Business Logic Errors (Show messages, stay on page)
#         if (response.status === 400) {
#             const errorData: ErrorResponse = await response.json();
#             alert(`Oops: ${errorData.message}`);
#             return;
#         }

#         // 3. Handle Success (Update UI or redirect to a dashboard)
#         if (response.ok) {
#             const responseData: SuccessResponse = await response.json();
#             console.log("Success!", responseData);
#             // JS can redirect the user after success:
#             window.location.href = '/dashboard'; 
#         }

#     } catch (error: unknown) {
#         if (error instanceof Error) {
#             console.error("Network error:", error.message);
#         } else {
#             console.error("Unknown network error:", error);
#         }
#     }
# }