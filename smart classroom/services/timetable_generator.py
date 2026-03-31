"""
Core Timetable Generation Service.

Bridges the ML pipeline with the database layer. Handles:
- Triggering generation for specific courses/semesters
- Saving generated timetables to the database
- Providing formatted output for the UI
- Managing generation history
"""

from database.models import (
    db, TimetableEntry, Subject, Faculty, Classroom, TimeSlot, Course,
)
from ml.pipeline import MLPipeline


class TimetableGenerator:
    """High-level service for generating and managing timetables."""

    def __init__(self, config):
        self.config = config
        self.pipeline = MLPipeline(config)

    def generate(self, course_id=None, semester=None, academic_year="2024-25"):
        """
        Generate a timetable and save it to the database.

        Step-by-step algorithm:
        1. Clear existing active entries for the target scope
        2. Run ML pipeline (train → optimize → validate)
        3. Save valid entries to timetable_entries table
        4. Return formatted result with statistics

        Returns:
            dict with status, entries_created, fitness, violations, ml_insights
        """
        # Step 1: Clear existing entries
        query = TimetableEntry.query.filter_by(academic_year=academic_year, is_active=True)
        if course_id:
            query = query.filter_by(course_id=course_id)
        if semester:
            query = query.filter_by(semester=semester)
        query.delete()
        db.session.commit()

        # Step 2: Run ML pipeline
        result = self.pipeline.generate_timetable(course_id, semester)

        if not result["timetable"]:
            return {
                "status": "failed",
                "message": "No timetable could be generated. Check data availability.",
                "entries_created": 0,
            }

        # Step 3: Save entries (skip duplicates using conflict detection)
        entries_created = 0
        skipped = 0
        occupied_faculty = set()
        occupied_rooms = set()

        for gene in result["timetable"]:
            fkey = (gene["faculty_id"], gene["timeslot_id"])
            rkey = (gene["classroom_id"], gene["timeslot_id"])

            # Skip if would create a conflict
            if fkey in occupied_faculty or rkey in occupied_rooms:
                skipped += 1
                continue

            entry = TimetableEntry(
                subject_id=gene["subject_id"],
                faculty_id=gene["faculty_id"],
                classroom_id=gene["classroom_id"],
                timeslot_id=gene["timeslot_id"],
                course_id=gene["course_id"],
                semester=gene["semester"],
                academic_year=academic_year,
                is_active=True,
            )
            db.session.add(entry)
            occupied_faculty.add(fkey)
            occupied_rooms.add(rkey)
            entries_created += 1

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {
                "status": "error",
                "message": str(e),
                "entries_created": 0,
            }

        return {
            "status": "success",
            "entries_created": entries_created,
            "entries_skipped": skipped,
            "fitness_score": result["fitness"],
            "violations": result["violations"],
            "ml_insights": result["ml_insights"],
            "stats": result["stats"],
        }

    def get_timetable(self, course_id=None, semester=None,
                      faculty_id=None, academic_year="2024-25"):
        """
        Retrieve the current timetable in a structured format.

        Returns a dict organized by day and period for easy grid display.
        """
        query = TimetableEntry.query.filter_by(
            academic_year=academic_year, is_active=True
        )
        if course_id:
            query = query.filter_by(course_id=course_id)
        if semester:
            query = query.filter_by(semester=semester)
        if faculty_id:
            query = query.filter_by(faculty_id=faculty_id)

        entries = query.all()

        # Build grid: {day: {period: [entries]}}
        grid = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        for day in days:
            grid[day] = {}
            for period in range(1, 9):
                grid[day][period] = []

        for entry in entries:
            ts = entry.time_slot
            if ts:
                grid[ts.day][ts.period_number].append(entry.to_dict())

        return {
            "grid": grid,
            "total_entries": len(entries),
            "days": days,
            "periods": list(range(1, 9)),
        }

    def get_timetable_list(self, course_id=None, semester=None,
                           faculty_id=None, academic_year="2024-25"):
        """Get timetable as a flat list of entries."""
        query = TimetableEntry.query.filter_by(
            academic_year=academic_year, is_active=True
        )
        if course_id:
            query = query.filter_by(course_id=course_id)
        if semester:
            query = query.filter_by(semester=semester)
        if faculty_id:
            query = query.filter_by(faculty_id=faculty_id)

        entries = query.all()
        return [e.to_dict() for e in entries]

    def reschedule_entry(self, entry_id, new_timeslot_id=None,
                         new_classroom_id=None, new_faculty_id=None):
        """
        Reschedule a single timetable entry dynamically.
        Checks for conflicts before applying changes.
        """
        entry = TimetableEntry.query.get(entry_id)
        if not entry:
            return {"status": "error", "message": "Entry not found"}

        # Check conflicts for the new assignment
        ts_id = new_timeslot_id or entry.timeslot_id
        room_id = new_classroom_id or entry.classroom_id
        fac_id = new_faculty_id or entry.faculty_id

        # Faculty conflict check
        conflict = TimetableEntry.query.filter(
            TimetableEntry.id != entry_id,
            TimetableEntry.faculty_id == fac_id,
            TimetableEntry.timeslot_id == ts_id,
            TimetableEntry.academic_year == entry.academic_year,
            TimetableEntry.is_active == True,
        ).first()
        if conflict:
            return {
                "status": "conflict",
                "message": f"Faculty already assigned at this time slot (entry #{conflict.id})",
            }

        # Room conflict check
        conflict = TimetableEntry.query.filter(
            TimetableEntry.id != entry_id,
            TimetableEntry.classroom_id == room_id,
            TimetableEntry.timeslot_id == ts_id,
            TimetableEntry.academic_year == entry.academic_year,
            TimetableEntry.is_active == True,
        ).first()
        if conflict:
            return {
                "status": "conflict",
                "message": f"Classroom already booked at this time slot (entry #{conflict.id})",
            }

        # Apply changes
        if new_timeslot_id:
            entry.timeslot_id = new_timeslot_id
        if new_classroom_id:
            entry.classroom_id = new_classroom_id
        if new_faculty_id:
            entry.faculty_id = new_faculty_id

        try:
            db.session.commit()
            return {"status": "success", "entry": entry.to_dict()}
        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}
