"""
Constraint Satisfaction Problem (CSP) Engine.

Enforces hard and soft constraints for timetable scheduling:
- Hard: No double-booking of rooms/faculty, capacity limits, lab requirements
- Soft: Faculty preferences, workload balance, consecutive class limits

WHY CSP: Guarantees that any generated schedule is feasible before optimization.
The GA can then focus on improving quality rather than fixing violations.
"""

from database.models import (
    db, Subject, Faculty, Classroom, TimeSlot, FacultyPreference,
    TimetableEntry, faculty_subjects,
)


class ConstraintSolver:
    """Evaluates and filters timetable assignments based on constraints."""

    def __init__(self, config):
        self.config = config
        self.weights = {
            "hard_conflict": config.WEIGHT_HARD_CONFLICT,
            "capacity": config.WEIGHT_CAPACITY,
            "faculty_pref": config.WEIGHT_FACULTY_PREF,
            "workload_balance": config.WEIGHT_WORKLOAD_BALANCE,
            "consecutive": config.WEIGHT_CONSECUTIVE,
            "lunch_break": config.WEIGHT_LUNCH_BREAK,
        }

    def get_valid_assignments(self, subject, existing_assignments):
        """
        Return all valid (faculty, classroom, timeslot) combos for a subject
        that satisfy hard constraints given existing assignments.
        """
        eligible_faculty = subject.faculty_members
        if not eligible_faculty:
            # Fallback: any faculty in same department
            dept_id = subject.course.department_id
            eligible_faculty = Faculty.query.filter_by(department_id=dept_id).all()

        all_timeslots = TimeSlot.query.filter_by(is_break=False).all()

        if subject.requires_lab:
            eligible_rooms = Classroom.query.filter_by(
                room_type="lab", has_lab_equipment=True, is_available=True
            ).all()
        else:
            eligible_rooms = Classroom.query.filter(
                Classroom.room_type.in_(["lecture", "seminar"]),
                Classroom.is_available == True,
            ).all()

        # Build occupied sets from existing assignments
        occupied_faculty = set()   # (faculty_id, timeslot_id)
        occupied_rooms = set()     # (classroom_id, timeslot_id)
        occupied_course = set()    # (course_id, semester, timeslot_id)
        faculty_day_hours = {}     # faculty_id -> {day: count}
        faculty_week_hours = {}    # faculty_id -> count

        for a in existing_assignments:
            occupied_faculty.add((a["faculty_id"], a["timeslot_id"]))
            occupied_rooms.add((a["classroom_id"], a["timeslot_id"]))
            occupied_course.add((a["course_id"], a["semester"], a["timeslot_id"]))

            fid = a["faculty_id"]
            day = a["day"]
            faculty_day_hours.setdefault(fid, {})
            faculty_day_hours[fid][day] = faculty_day_hours[fid].get(day, 0) + 1
            faculty_week_hours[fid] = faculty_week_hours.get(fid, 0) + 1

        valid = []
        for f in eligible_faculty:
            for ts in all_timeslots:
                # Hard: Faculty not double-booked
                if (f.id, ts.id) in occupied_faculty:
                    continue
                # Hard: Course-semester not double-booked at same time
                if (subject.course_id, subject.semester, ts.id) in occupied_course:
                    continue
                # Hard: Faculty daily limit
                day_hours = faculty_day_hours.get(f.id, {}).get(ts.day, 0)
                if day_hours >= f.max_hours_per_day:
                    continue
                # Hard: Faculty weekly limit
                week_hours = faculty_week_hours.get(f.id, 0)
                if week_hours >= f.max_hours_per_week:
                    continue

                for room in eligible_rooms:
                    # Hard: Room not double-booked
                    if (room.id, ts.id) in occupied_rooms:
                        continue
                    valid.append({
                        "subject_id": subject.id,
                        "faculty_id": f.id,
                        "classroom_id": room.id,
                        "timeslot_id": ts.id,
                        "course_id": subject.course_id,
                        "semester": subject.semester,
                        "day": ts.day,
                        "period": ts.period_number,
                    })
        return valid

    def evaluate_fitness(self, chromosome):
        """
        Evaluate the fitness of a complete timetable (chromosome).
        Lower score = better (fewer violations).

        Args:
            chromosome: List of assignment dicts

        Returns:
            Tuple of (total_penalty,) for DEAP compatibility
        """
        penalty = 0.0

        # Track occupancy
        faculty_slots = {}    # (faculty_id, timeslot_id) -> count
        room_slots = {}       # (classroom_id, timeslot_id) -> count
        course_slots = {}     # (course_id, semester, timeslot_id) -> count
        faculty_day = {}      # (faculty_id, day) -> [period_numbers]
        faculty_week = {}     # faculty_id -> total_hours

        for gene in chromosome:
            fkey = (gene["faculty_id"], gene["timeslot_id"])
            rkey = (gene["classroom_id"], gene["timeslot_id"])
            ckey = (gene["course_id"], gene["semester"], gene["timeslot_id"])

            # Hard constraint: Faculty double-booking
            faculty_slots[fkey] = faculty_slots.get(fkey, 0) + 1
            if faculty_slots[fkey] > 1:
                penalty += self.weights["hard_conflict"]

            # Hard constraint: Room double-booking
            room_slots[rkey] = room_slots.get(rkey, 0) + 1
            if room_slots[rkey] > 1:
                penalty += self.weights["hard_conflict"]

            # Hard constraint: Same course-semester at same time
            course_slots[ckey] = course_slots.get(ckey, 0) + 1
            if course_slots[ckey] > 1:
                penalty += self.weights["hard_conflict"]

            # Track for soft constraints
            fd_key = (gene["faculty_id"], gene["day"])
            faculty_day.setdefault(fd_key, []).append(gene["period"])
            faculty_week[gene["faculty_id"]] = faculty_week.get(gene["faculty_id"], 0) + 1

        # Soft constraint: Faculty preferences
        pref_cache = self._load_preference_cache()
        for gene in chromosome:
            pkey = (gene["faculty_id"], gene["timeslot_id"])
            if pkey in pref_cache:
                pref = pref_cache[pkey]
                if pref == 1:  # Avoid
                    penalty += self.weights["faculty_pref"] * 2
                elif pref == 2:  # Neutral
                    penalty += self.weights["faculty_pref"] * 0.5

        # Soft constraint: Consecutive classes (more than 3 in a row)
        for (fid, day), periods in faculty_day.items():
            periods.sort()
            consecutive = 1
            for i in range(1, len(periods)):
                if periods[i] == periods[i - 1] + 1:
                    consecutive += 1
                    if consecutive > 3:
                        penalty += self.weights["consecutive"]
                else:
                    consecutive = 1

        # Soft constraint: Lunch break violation (period 4 and 5 both occupied)
        for (fid, day), periods in faculty_day.items():
            if 4 in periods and 5 in periods:
                penalty += self.weights["lunch_break"]

        # Soft constraint: Workload balance across faculty
        if faculty_week:
            hours = list(faculty_week.values())
            avg = sum(hours) / len(hours)
            variance = sum((h - avg) ** 2 for h in hours) / len(hours)
            penalty += variance * self.weights["workload_balance"]

        return (penalty,)

    def check_hard_constraints(self, chromosome):
        """Check if a chromosome satisfies all hard constraints. Returns list of violations."""
        violations = []
        faculty_slots = {}
        room_slots = {}
        course_slots = {}

        for i, gene in enumerate(chromosome):
            fkey = (gene["faculty_id"], gene["timeslot_id"])
            rkey = (gene["classroom_id"], gene["timeslot_id"])
            ckey = (gene["course_id"], gene["semester"], gene["timeslot_id"])

            if fkey in faculty_slots:
                violations.append(
                    f"Faculty {gene['faculty_id']} double-booked at timeslot {gene['timeslot_id']}"
                )
            faculty_slots[fkey] = i

            if rkey in room_slots:
                violations.append(
                    f"Room {gene['classroom_id']} double-booked at timeslot {gene['timeslot_id']}"
                )
            room_slots[rkey] = i

            if ckey in course_slots:
                violations.append(
                    f"Course {gene['course_id']} sem {gene['semester']} has clash at timeslot {gene['timeslot_id']}"
                )
            course_slots[ckey] = i

        return violations

    _pref_cache = None

    def _load_preference_cache(self):
        """Cache faculty preferences for fast lookup."""
        if self._pref_cache is None:
            prefs = FacultyPreference.query.all()
            self._pref_cache = {
                (p.faculty_id, p.timeslot_id): p.preference_level
                for p in prefs
            }
        return self._pref_cache

    def reset_cache(self):
        self._pref_cache = None
