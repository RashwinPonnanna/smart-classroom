"""
Student Module Routes.

Handles:
- View timetable by course/semester
- View classroom details
- Get schedule notifications
"""

from flask import Blueprint, render_template, request
from database.models import db, Course, Student, Classroom, TimeSlot
from services.timetable_generator import TimetableGenerator
from config import Config

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/timetable")
def timetable():
    courses = Course.query.all()
    course_id = request.args.get("course_id", type=int)
    semester = request.args.get("semester", 5, type=int)

    timetable_data = None
    time_slots = {}

    if course_id:
        generator = TimetableGenerator(Config)
        timetable_data = generator.get_timetable(course_id=course_id, semester=semester)

        for ts in TimeSlot.query.filter_by(is_break=False).all():
            time_slots[ts.period_number] = f"{ts.start_time}-{ts.end_time}"

    return render_template(
        "student/timetable.html",
        courses=courses,
        timetable=timetable_data,
        selected_course=course_id,
        selected_semester=semester,
        time_slots=time_slots,
    )


@student_bp.route("/classrooms")
def classrooms():
    rooms = Classroom.query.filter_by(is_available=True).all()
    return render_template(
        "student/timetable.html",
        classrooms=[r.to_dict() for r in rooms],
        show_classrooms=True,
        courses=Course.query.all(),
    )
