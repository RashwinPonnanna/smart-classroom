"""
Smart Classroom Timetable Scheduler - Application Entry Point.

This is the main Flask application that wires together:
- Database models (SQLAlchemy + SQLite)
- Route blueprints (Admin, Faculty, Student, API)
- ML pipeline integration
- Seed data initialization
"""

import os
from flask import Flask, redirect, url_for
from config import Config
from database.models import db


def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)

    # Register route blueprints
    from routes.admin import admin_bp
    from routes.faculty import faculty_bp
    from routes.student import student_bp
    from routes.api import api_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)

    # Root redirect
    @app.route("/")
    def index():
        return redirect(url_for("admin.dashboard"))

    # Create tables and seed data on first run
    with app.app_context():
        db.create_all()

        # Check if data already exists
        from database.models import Department
        if Department.query.count() == 0:
            print("No data found. Seeding database...")
            from database.seed_data import seed_all
            seed_all()
        else:
            print(f"Database loaded: {Department.query.count()} departments found.")

    return app


if __name__ == "__main__":
    app = create_app()
    print("\n" + "=" * 60)
    print("  Smart Classroom Timetable Scheduler")
    print("  ML-Powered Academic Schedule Optimization")
    print("=" * 60)
    print(f"  Server: http://127.0.0.1:5000")
    print(f"  Admin:  http://127.0.0.1:5000/admin/dashboard")
    print(f"  Faculty: http://127.0.0.1:5000/faculty/schedule")
    print(f"  Student: http://127.0.0.1:5000/student/timetable")
    print(f"  API:    http://127.0.0.1:5000/api/analytics")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000)
