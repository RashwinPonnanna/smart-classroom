"""
Conflict Detection and Resolution Service.

Detects scheduling conflicts and suggests resolution strategies:
- Faculty double-booking
- Room double-booking
- Course-semester overlap
- Capacity violations
"""

from database.models import (
    db, TimetableEntry, Subject, Faculty, Classroom, TimeSlot,
)
from collections import defaultdict


class ConflictResolver:
    """Detects and resolves timetable conflicts."""

    def detect_conflicts(self, academic_year="2024-25"):
        """
        Scan the active timetable for all types of conflicts.

        Returns:
            List of conflict dicts with type, details, affected entries
        """
        entries = TimetableEntry.query.filter_by(
            academic_year=academic_year, is_active=True
        ).all()

        conflicts = []

        # Group by faculty-timeslot
        faculty_slots = defaultdict(list)
        # Group by room-timeslot
        room_slots = defaultdict(list)
        # Group by course-semester-timeslot
        course_slots = defaultdict(list)

        for entry in entries:
            faculty_slots[(entry.faculty_id, entry.timeslot_id)].append(entry)
            room_slots[(entry.classroom_id, entry.timeslot_id)].append(entry)
            course_slots[(entry.course_id, entry.semester, entry.timeslot_id)].append(entry)

        # Faculty double-booking
        for key, elist in faculty_slots.items():
            if len(elist) > 1:
                faculty = Faculty.query.get(key[0])
                ts = TimeSlot.query.get(key[1])
                conflicts.append({
                    "type": "faculty_double_booking",
                    "severity": "critical",
                    "description": f"{faculty.name} is double-booked on {ts.day} period {ts.period_number}",
                    "affected_entries": [e.id for e in elist],
                    "faculty_id": key[0],
                    "timeslot_id": key[1],
                })

        # Room double-booking
        for key, elist in room_slots.items():
            if len(elist) > 1:
                room = Classroom.query.get(key[0])
                ts = TimeSlot.query.get(key[1])
                conflicts.append({
                    "type": "room_double_booking",
                    "severity": "critical",
                    "description": f"Room {room.name} is double-booked on {ts.day} period {ts.period_number}",
                    "affected_entries": [e.id for e in elist],
                    "classroom_id": key[0],
                    "timeslot_id": key[1],
                })

        # Course overlap
        for key, elist in course_slots.items():
            if len(elist) > 1:
                conflicts.append({
                    "type": "course_overlap",
                    "severity": "critical",
                    "description": f"Course {key[0]} sem {key[1]} has overlapping classes",
                    "affected_entries": [e.id for e in elist],
                })

        # Capacity violations
        for entry in entries:
            room = entry.classroom
            if room:
                from database.models import Student
                student_count = Student.query.filter_by(
                    course_id=entry.course_id, semester=entry.semester
                ).count()
                if student_count > room.capacity:
                    conflicts.append({
                        "type": "capacity_violation",
                        "severity": "warning",
                        "description": (
                            f"Room {room.name} (capacity {room.capacity}) "
                            f"assigned to {student_count} students"
                        ),
                        "affected_entries": [entry.id],
                        "classroom_id": room.id,
                    })

        return conflicts

    def suggest_resolution(self, conflict):
        """
        Suggest possible resolutions for a specific conflict.

        Returns list of suggested actions.
        """
        suggestions = []

        if conflict["type"] == "faculty_double_booking":
            # Find alternative time slots for one of the affected entries
            entry_id = conflict["affected_entries"][1]  # Move the second one
            entry = TimetableEntry.query.get(entry_id)
            if entry:
                free_slots = self._find_free_faculty_slots(
                    entry.faculty_id, entry.academic_year
                )
                for slot in free_slots[:3]:
                    suggestions.append({
                        "action": "move_entry",
                        "entry_id": entry_id,
                        "new_timeslot_id": slot.id,
                        "description": f"Move to {slot.day} period {slot.period_number} ({slot.start_time})",
                    })

        elif conflict["type"] == "room_double_booking":
            entry_id = conflict["affected_entries"][1]
            entry = TimetableEntry.query.get(entry_id)
            if entry:
                free_rooms = self._find_free_rooms(
                    entry.timeslot_id, entry.academic_year,
                    needs_lab=entry.subject.requires_lab if entry.subject else False,
                )
                for room in free_rooms[:3]:
                    suggestions.append({
                        "action": "change_room",
                        "entry_id": entry_id,
                        "new_classroom_id": room.id,
                        "description": f"Move to room {room.name} ({room.building}, cap: {room.capacity})",
                    })

        elif conflict["type"] == "capacity_violation":
            entry_id = conflict["affected_entries"][0]
            entry = TimetableEntry.query.get(entry_id)
            if entry:
                from database.models import Student
                needed = Student.query.filter_by(
                    course_id=entry.course_id, semester=entry.semester
                ).count()
                larger_rooms = Classroom.query.filter(
                    Classroom.capacity >= needed,
                    Classroom.is_available == True,
                ).order_by(Classroom.capacity).all()

                # Check which are free at this timeslot
                for room in larger_rooms[:5]:
                    occupied = TimetableEntry.query.filter_by(
                        classroom_id=room.id,
                        timeslot_id=entry.timeslot_id,
                        academic_year=entry.academic_year,
                        is_active=True,
                    ).first()
                    if not occupied:
                        suggestions.append({
                            "action": "change_room",
                            "entry_id": entry_id,
                            "new_classroom_id": room.id,
                            "description": f"Move to {room.name} (capacity {room.capacity})",
                        })

        return suggestions

    def auto_resolve(self, academic_year="2024-25"):
        """
        Attempt to automatically resolve all conflicts.

        Returns summary of resolved and unresolved conflicts.
        """
        conflicts = self.detect_conflicts(academic_year)
        resolved = 0
        unresolved = []

        for conflict in conflicts:
            suggestions = self.suggest_resolution(conflict)
            if suggestions:
                # Apply the first suggestion
                s = suggestions[0]
                entry = TimetableEntry.query.get(s["entry_id"])
                if entry:
                    if "new_timeslot_id" in s:
                        entry.timeslot_id = s["new_timeslot_id"]
                    if "new_classroom_id" in s:
                        entry.classroom_id = s["new_classroom_id"]
                    resolved += 1
            else:
                unresolved.append(conflict)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        return {
            "total_conflicts": len(conflicts),
            "resolved": resolved,
            "unresolved": len(unresolved),
            "unresolved_details": unresolved,
        }

    def _find_free_faculty_slots(self, faculty_id, academic_year):
        """Find time slots where a faculty member is free."""
        occupied_ids = {
            e.timeslot_id for e in
            TimetableEntry.query.filter_by(
                faculty_id=faculty_id, academic_year=academic_year, is_active=True
            ).all()
        }
        return TimeSlot.query.filter(
            ~TimeSlot.id.in_(occupied_ids),
            TimeSlot.is_break == False,
        ).all()

    def _find_free_rooms(self, timeslot_id, academic_year, needs_lab=False):
        """Find classrooms free at a specific time slot."""
        occupied_ids = {
            e.classroom_id for e in
            TimetableEntry.query.filter_by(
                timeslot_id=timeslot_id, academic_year=academic_year, is_active=True
            ).all()
        }
        query = Classroom.query.filter(
            ~Classroom.id.in_(occupied_ids),
            Classroom.is_available == True,
        )
        if needs_lab:
            query = query.filter_by(room_type="lab", has_lab_equipment=True)
        else:
            query = query.filter(Classroom.room_type.in_(["lecture", "seminar"]))
        return query.all()
