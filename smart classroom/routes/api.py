"""
REST API Routes.

Provides JSON endpoints for AJAX operations and external integrations.
"""

from flask import Blueprint, jsonify, request
from database.models import (
    db, Department, Course, Subject, Faculty, Classroom,
    TimeSlot, TimetableEntry, Student,
)
from services.timetable_generator import TimetableGenerator
from services.conflict_resolver import ConflictResolver
from services.analytics import AnalyticsService
from config import Config

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/analytics")
def analytics():
    service = AnalyticsService()
    return jsonify({
        "stats": service.get_dashboard_stats(),
        "room_utilization": service.get_room_utilization(),
        "faculty_workload": service.get_faculty_workload(),
        "department_summary": service.get_department_summary(),
        "time_distribution": service.get_time_distribution(),
    })


@api_bp.route("/timetable")
def get_timetable():
    course_id = request.args.get("course_id", type=int)
    semester = request.args.get("semester", type=int)
    faculty_id = request.args.get("faculty_id", type=int)

    generator = TimetableGenerator(Config)
    data = generator.get_timetable(
        course_id=course_id, semester=semester, faculty_id=faculty_id,
    )
    return jsonify(data)


@api_bp.route("/timetable/generate", methods=["POST"])
def generate():
    data = request.get_json() or {}
    course_id = data.get("course_id")
    semester = data.get("semester", 5)

    generator = TimetableGenerator(Config)
    result = generator.generate(course_id=course_id, semester=semester)
    return jsonify(result)


@api_bp.route("/timetable/entry/<int:entry_id>/reschedule", methods=["POST"])
def reschedule(entry_id):
    data = request.get_json() or {}
    generator = TimetableGenerator(Config)
    result = generator.reschedule_entry(
        entry_id,
        new_timeslot_id=data.get("timeslot_id"),
        new_classroom_id=data.get("classroom_id"),
        new_faculty_id=data.get("faculty_id"),
    )
    return jsonify(result)


@api_bp.route("/conflicts")
def conflicts():
    resolver = ConflictResolver()
    conflict_list = resolver.detect_conflicts()
    return jsonify({"conflicts": conflict_list, "total": len(conflict_list)})


@api_bp.route("/conflicts/resolve", methods=["POST"])
def resolve_conflicts():
    resolver = ConflictResolver()
    result = resolver.auto_resolve()
    return jsonify(result)


# --- Entity APIs ---

@api_bp.route("/departments")
def departments():
    return jsonify([d.to_dict() for d in Department.query.all()])


@api_bp.route("/courses")
def courses():
    return jsonify([c.to_dict() for c in Course.query.all()])


@api_bp.route("/subjects")
def subjects():
    course_id = request.args.get("course_id", type=int)
    query = Subject.query
    if course_id:
        query = query.filter_by(course_id=course_id)
    return jsonify([s.to_dict() for s in query.all()])


@api_bp.route("/faculty")
def faculty():
    dept_id = request.args.get("department_id", type=int)
    query = Faculty.query
    if dept_id:
        query = query.filter_by(department_id=dept_id)
    return jsonify([f.to_dict() for f in query.all()])


@api_bp.route("/classrooms")
def classrooms():
    return jsonify([c.to_dict() for c in Classroom.query.all()])


@api_bp.route("/timeslots")
def timeslots():
    return jsonify([t.to_dict() for t in TimeSlot.query.filter_by(is_break=False).all()])


@api_bp.route("/students")
def students():
    course_id = request.args.get("course_id", type=int)
    query = Student.query
    if course_id:
        query = query.filter_by(course_id=course_id)
    return jsonify([s.to_dict() for s in query.all()])
