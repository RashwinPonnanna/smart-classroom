"""
Admin Module Routes.

Handles:
- Dashboard with analytics
- CRUD for departments, courses, subjects, faculty, classrooms
- Timetable generation and management
- Conflict detection and resolution
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.models import (
    db, Department, Course, Subject, Faculty, Classroom,
    TimeSlot, TimetableEntry, Student,
)
from services.timetable_generator import TimetableGenerator
from services.conflict_resolver import ConflictResolver
from services.analytics import AnalyticsService
from config import Config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
def dashboard():
    analytics = AnalyticsService()
    stats = analytics.get_dashboard_stats()
    return render_template("admin/dashboard.html", stats=stats)


@admin_bp.route("/manage")
def manage():
    entity = request.args.get("entity", "departments")
    items = []
    departments = []
    courses = []

    if entity == "departments":
        items = [d.to_dict() for d in Department.query.all()]
    elif entity == "courses":
        items = [c.to_dict() for c in Course.query.all()]
        departments = [d.to_dict() for d in Department.query.all()]
    elif entity == "subjects":
        items = [s.to_dict() for s in Subject.query.all()]
        courses = [c.to_dict() for c in Course.query.all()]
    elif entity == "faculty":
        items = [f.to_dict() for f in Faculty.query.all()]
        departments = [d.to_dict() for d in Department.query.all()]
    elif entity == "classrooms":
        items = [c.to_dict() for c in Classroom.query.all()]
    elif entity == "students":
        items = [s.to_dict() for s in Student.query.all()]
        courses = [c.to_dict() for c in Course.query.all()]

    return render_template("admin/manage.html", entity=entity, items=items, departments=departments, courses=courses)


# --- CRUD API endpoints for admin ---

@admin_bp.route("/api/department", methods=["POST"])
def add_department():
    name = request.form.get("name")
    code = request.form.get("code")
    if name and code:
        dept = Department(name=name, code=code.upper())
        db.session.add(dept)
        db.session.commit()
        flash(f"Department '{name}' added successfully.", "success")
    else:
        flash("Name and code are required.", "error")
    return redirect(url_for("admin.manage", entity="departments"))


@admin_bp.route("/api/department/<int:dept_id>/delete", methods=["POST"])
def delete_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    db.session.delete(dept)
    db.session.commit()
    flash(f"Department '{dept.name}' deleted.", "success")
    return redirect(url_for("admin.manage", entity="departments"))


@admin_bp.route("/api/course", methods=["POST"])
def add_course():
    name = request.form.get("name")
    code = request.form.get("code")
    dept_id = request.form.get("department_id")
    if name and code and dept_id:
        course = Course(name=name, code=code.upper(), department_id=int(dept_id))
        db.session.add(course)
        db.session.commit()
        flash(f"Course '{name}' added.", "success")
    return redirect(url_for("admin.manage", entity="courses"))


@admin_bp.route("/api/subject", methods=["POST"])
def add_subject():
    s = Subject(
        name=request.form.get("name"),
        code=request.form.get("code", "").upper(),
        course_id=int(request.form.get("course_id")),
        semester=int(request.form.get("semester", 5)),
        subject_type=request.form.get("subject_type", "theory"),
        hours_per_week=int(request.form.get("hours_per_week", 3)),
        requires_lab="requires_lab" in request.form,
        priority=int(request.form.get("priority", 5)),
    )
    db.session.add(s)
    db.session.commit()
    flash(f"Subject '{s.name}' added.", "success")
    return redirect(url_for("admin.manage", entity="subjects"))


@admin_bp.route("/api/faculty", methods=["POST"])
def add_faculty():
    f = Faculty(
        name=request.form.get("name"),
        email=request.form.get("email"),
        department_id=int(request.form.get("department_id")),
        designation=request.form.get("designation", "Assistant Professor"),
        max_hours_per_week=int(request.form.get("max_hours_per_week", 20)),
        max_hours_per_day=int(request.form.get("max_hours_per_day", 5)),
    )
    db.session.add(f)
    db.session.commit()
    flash(f"Faculty '{f.name}' added.", "success")
    return redirect(url_for("admin.manage", entity="faculty"))


@admin_bp.route("/api/classroom", methods=["POST"])
def add_classroom():
    c = Classroom(
        name=request.form.get("name"),
        building=request.form.get("building", "Main"),
        capacity=int(request.form.get("capacity", 40)),
        room_type=request.form.get("room_type", "lecture"),
        has_projector="has_projector" in request.form,
        has_lab_equipment="has_lab_equipment" in request.form,
    )
    db.session.add(c)
    db.session.commit()
    flash(f"Classroom '{c.name}' added.", "success")
    return redirect(url_for("admin.manage", entity="classrooms"))


# --- Timetable Generation ---

@admin_bp.route("/timetable")
def timetable():
    courses = Course.query.all()
    course_id = request.args.get("course_id", type=int)
    semester = request.args.get("semester", 5, type=int)

    generator = TimetableGenerator(Config)
    timetable_data = generator.get_timetable(course_id=course_id, semester=semester)

    # Get time slot info for display
    time_slots = {}
    for ts in TimeSlot.query.filter_by(is_break=False).all():
        time_slots[ts.period_number] = f"{ts.start_time}-{ts.end_time}"

    return render_template(
        "admin/timetable.html",
        timetable=timetable_data,
        courses=courses,
        selected_course=course_id,
        selected_semester=semester,
        time_slots=time_slots,
    )


@admin_bp.route("/generate", methods=["POST"])
def generate_timetable():
    course_id = request.form.get("course_id", type=int)
    semester = request.form.get("semester", 5, type=int)

    generator = TimetableGenerator(Config)
    result = generator.generate(course_id=course_id, semester=semester)

    if result["status"] == "success":
        flash(
            f"Timetable generated! {result['entries_created']} entries created. "
            f"Fitness: {result['fitness_score']:.1f}",
            "success",
        )
    else:
        flash(f"Generation failed: {result.get('message', 'Unknown error')}", "error")

    return redirect(url_for("admin.timetable", course_id=course_id, semester=semester))


@admin_bp.route("/conflicts")
def conflicts():
    resolver = ConflictResolver()
    conflict_list = resolver.detect_conflicts()
    return render_template("admin/dashboard.html",
                           conflicts=conflict_list,
                           stats=AnalyticsService().get_dashboard_stats())


@admin_bp.route("/auto-resolve", methods=["POST"])
def auto_resolve():
    resolver = ConflictResolver()
    result = resolver.auto_resolve()
    flash(
        f"Resolved {result['resolved']}/{result['total_conflicts']} conflicts.",
        "success" if result["unresolved"] == 0 else "warning",
    )
    return redirect(url_for("admin.dashboard"))
