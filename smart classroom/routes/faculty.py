"""
Faculty Module Routes.

Handles:
- View personal schedule
- Set availability preferences
- Request schedule swaps
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.models import (
    db, Faculty, TimeSlot, TimetableEntry, FacultyPreference,
)
from services.timetable_generator import TimetableGenerator
from config import Config

faculty_bp = Blueprint("faculty", __name__, url_prefix="/faculty")


@faculty_bp.route("/schedule")
def schedule():
    faculty_list = Faculty.query.all()
    faculty_id = request.args.get("faculty_id", type=int)

    schedule_data = None
    selected_faculty = None
    time_slots = {}

    if faculty_id:
        selected_faculty = Faculty.query.get(faculty_id)
        generator = TimetableGenerator(Config)
        schedule_data = generator.get_timetable(faculty_id=faculty_id)

        for ts in TimeSlot.query.filter_by(is_break=False).all():
            time_slots[ts.period_number] = f"{ts.start_time}-{ts.end_time}"

    return render_template(
        "faculty/schedule.html",
        faculty_list=faculty_list,
        schedule=schedule_data,
        selected_faculty=selected_faculty,
        time_slots=time_slots,
    )


@faculty_bp.route("/preferences", methods=["GET", "POST"])
def preferences():
    faculty_id = request.args.get("faculty_id", type=int)

    if request.method == "POST":
        faculty_id = int(request.form.get("faculty_id"))
        # Clear existing preferences
        FacultyPreference.query.filter_by(faculty_id=faculty_id).delete()

        # Save new preferences
        time_slots = TimeSlot.query.filter_by(is_break=False).all()
        for ts in time_slots:
            level = request.form.get(f"pref_{ts.id}", type=int)
            if level and level != 3:  # Only save non-default preferences
                pref = FacultyPreference(
                    faculty_id=faculty_id,
                    timeslot_id=ts.id,
                    preference_level=level,
                )
                db.session.add(pref)

        db.session.commit()
        flash("Preferences saved successfully.", "success")
        return redirect(url_for("faculty.schedule", faculty_id=faculty_id))

    faculty_list = Faculty.query.all()
    time_slots = TimeSlot.query.filter_by(is_break=False).all()
    existing_prefs = {}

    if faculty_id:
        prefs = FacultyPreference.query.filter_by(faculty_id=faculty_id).all()
        existing_prefs = {p.timeslot_id: p.preference_level for p in prefs}

    return render_template(
        "faculty/schedule.html",
        faculty_list=faculty_list,
        time_slots_list=time_slots,
        existing_prefs=existing_prefs,
        selected_faculty=Faculty.query.get(faculty_id) if faculty_id else None,
        show_preferences=True,
    )


@faculty_bp.route("/swap-request", methods=["POST"])
def swap_request():
    entry_id = request.form.get("entry_id", type=int)
    new_timeslot_id = request.form.get("new_timeslot_id", type=int)

    if entry_id and new_timeslot_id:
        generator = TimetableGenerator(Config)
        result = generator.reschedule_entry(entry_id, new_timeslot_id=new_timeslot_id)

        if result["status"] == "success":
            flash("Schedule swap applied successfully.", "success")
        else:
            flash(f"Swap failed: {result['message']}", "error")
    else:
        flash("Invalid swap request.", "error")

    faculty_id = request.form.get("faculty_id")
    return redirect(url_for("faculty.schedule", faculty_id=faculty_id))
