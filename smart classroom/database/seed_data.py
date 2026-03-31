"""
Seed data for Smart Classroom Timetable Scheduler.
Populates the database with realistic sample data for demonstration.
"""

import random
from database.models import (
    db, Department, Course, Subject, Faculty, Classroom,
    TimeSlot, Student, FacultyPreference, ScheduleHistory,
    faculty_subjects,
)


def seed_time_slots():
    """Create time slots for Mon-Fri, 8 periods per day."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [
        (1, "09:00", "09:50"),
        (2, "09:50", "10:40"),
        (3, "10:50", "11:40"),  # 10-min break
        (4, "11:40", "12:30"),
        (5, "13:10", "14:00"),  # Lunch break 12:30-13:10
        (6, "14:00", "14:50"),
        (7, "15:00", "15:50"),  # 10-min break
        (8, "15:50", "16:40"),
    ]
    slots = []
    for day in days:
        for period_num, start, end in periods:
            slot = TimeSlot(
                day=day,
                period_number=period_num,
                start_time=start,
                end_time=end,
                is_break=False,
            )
            slots.append(slot)
    db.session.add_all(slots)
    db.session.commit()
    return slots


def seed_departments():
    """Create academic departments."""
    departments = [
        Department(name="Computer Science & Engineering", code="CSE"),
        Department(name="Electronics & Communication", code="ECE"),
        Department(name="Mechanical Engineering", code="ME"),
        Department(name="Information Technology", code="IT"),
    ]
    db.session.add_all(departments)
    db.session.commit()
    return departments


def seed_courses(departments):
    """Create courses under each department."""
    courses_data = [
        ("B.Tech Computer Science", "BTCS", departments[0].id, 8),
        ("B.Tech Electronics", "BTEC", departments[1].id, 8),
        ("B.Tech Mechanical", "BTME", departments[2].id, 8),
        ("B.Tech Information Technology", "BTIT", departments[3].id, 8),
    ]
    courses = []
    for name, code, dept_id, sems in courses_data:
        c = Course(name=name, code=code, department_id=dept_id, total_semesters=sems)
        courses.append(c)
    db.session.add_all(courses)
    db.session.commit()
    return courses


def seed_subjects(courses):
    """Create subjects for semester 5 of each course."""
    subjects_map = {
        0: [  # CSE
            ("Data Structures & Algorithms", "CS301", "theory", 4, False, 2),
            ("Database Management Systems", "CS302", "theory", 3, False, 3),
            ("Operating Systems", "CS303", "theory", 4, False, 2),
            ("Computer Networks", "CS304", "theory", 3, False, 4),
            ("Software Engineering", "CS305", "theory", 3, False, 5),
            ("DSA Lab", "CS391", "lab", 2, True, 3),
            ("DBMS Lab", "CS392", "lab", 2, True, 4),
        ],
        1: [  # ECE
            ("Digital Signal Processing", "EC301", "theory", 4, False, 2),
            ("Microprocessors", "EC302", "theory", 3, False, 3),
            ("Communication Systems", "EC303", "theory", 4, False, 2),
            ("VLSI Design", "EC304", "theory", 3, False, 4),
            ("Embedded Systems", "EC305", "theory", 3, False, 5),
            ("DSP Lab", "EC391", "lab", 2, True, 3),
            ("Microprocessor Lab", "EC392", "lab", 2, True, 4),
        ],
        2: [  # ME
            ("Thermodynamics", "ME301", "theory", 4, False, 2),
            ("Fluid Mechanics", "ME302", "theory", 3, False, 3),
            ("Machine Design", "ME303", "theory", 4, False, 2),
            ("Manufacturing Processes", "ME304", "theory", 3, False, 4),
            ("Engineering Materials", "ME305", "theory", 3, False, 5),
            ("Thermo Lab", "ME391", "lab", 2, True, 3),
            ("Fluid Lab", "ME392", "lab", 2, True, 4),
        ],
        3: [  # IT
            ("Web Technologies", "IT301", "theory", 4, False, 2),
            ("Information Security", "IT302", "theory", 3, False, 3),
            ("Cloud Computing", "IT303", "theory", 4, False, 2),
            ("Data Mining", "IT304", "theory", 3, False, 4),
            ("Mobile App Development", "IT305", "theory", 3, False, 5),
            ("Web Lab", "IT391", "lab", 2, True, 3),
            ("Cloud Lab", "IT392", "lab", 2, True, 4),
        ],
    }

    all_subjects = []
    for idx, course in enumerate(courses):
        for name, code, stype, hours, lab, priority in subjects_map[idx]:
            s = Subject(
                name=name,
                code=code,
                course_id=course.id,
                semester=5,
                subject_type=stype,
                hours_per_week=hours,
                requires_lab=lab,
                priority=priority,
            )
            all_subjects.append(s)
    db.session.add_all(all_subjects)
    db.session.commit()
    return all_subjects


def seed_faculty(departments, subjects):
    """Create faculty members and assign subjects."""
    faculty_data = [
        # CSE
        ("Dr. Anand Kumar", "anand@univ.edu", 0, "Professor", 16, 4),
        ("Prof. Priya Sharma", "priya@univ.edu", 0, "Associate Professor", 18, 5),
        ("Dr. Rajesh Verma", "rajesh@univ.edu", 0, "Assistant Professor", 20, 5),
        ("Prof. Sneha Gupta", "sneha@univ.edu", 0, "Assistant Professor", 20, 5),
        # ECE
        ("Dr. Suresh Reddy", "suresh@univ.edu", 1, "Professor", 16, 4),
        ("Prof. Meera Patel", "meera@univ.edu", 1, "Associate Professor", 18, 5),
        ("Dr. Vikram Singh", "vikram@univ.edu", 1, "Assistant Professor", 20, 5),
        ("Prof. Kavita Rao", "kavita@univ.edu", 1, "Assistant Professor", 20, 5),
        # ME
        ("Dr. Arun Joshi", "arun@univ.edu", 2, "Professor", 16, 4),
        ("Prof. Deepa Nair", "deepa@univ.edu", 2, "Associate Professor", 18, 5),
        ("Dr. Mohan Das", "mohan@univ.edu", 2, "Assistant Professor", 20, 5),
        ("Prof. Rekha Iyer", "rekha@univ.edu", 2, "Assistant Professor", 20, 5),
        # IT
        ("Dr. Sanjay Mishra", "sanjay@univ.edu", 3, "Professor", 16, 4),
        ("Prof. Neha Kapoor", "neha@univ.edu", 3, "Associate Professor", 18, 5),
        ("Dr. Amit Tiwari", "amit@univ.edu", 3, "Assistant Professor", 20, 5),
        ("Prof. Ritu Saxena", "ritu@univ.edu", 3, "Assistant Professor", 20, 5),
    ]

    all_faculty = []
    for name, email, dept_idx, desig, max_week, max_day in faculty_data:
        f = Faculty(
            name=name,
            email=email,
            department_id=departments[dept_idx].id,
            designation=desig,
            max_hours_per_week=max_week,
            max_hours_per_day=max_day,
        )
        all_faculty.append(f)
    db.session.add_all(all_faculty)
    db.session.commit()

    # Assign subjects to faculty (each dept has 7 subjects, 4 faculty)
    dept_subjects = {}
    for s in subjects:
        course = Course.query.get(s.course_id)
        dept_id = course.department_id
        if dept_id not in dept_subjects:
            dept_subjects[dept_id] = []
        dept_subjects[dept_id].append(s)

    for f in all_faculty:
        dept_subs = dept_subjects.get(f.department_id, [])
        # Assign 2-3 subjects per faculty
        assigned = random.sample(dept_subs, min(3, len(dept_subs)))
        for s in assigned:
            f.subjects.append(s)

    db.session.commit()
    return all_faculty


def seed_classrooms():
    """Create classrooms and labs."""
    rooms = [
        # Lecture halls
        ("LH-101", "Block A", 60, "lecture", True, False),
        ("LH-102", "Block A", 60, "lecture", True, False),
        ("LH-103", "Block A", 45, "lecture", True, False),
        ("LH-201", "Block B", 60, "lecture", True, False),
        ("LH-202", "Block B", 45, "lecture", True, False),
        ("LH-203", "Block B", 40, "lecture", True, False),
        ("LH-301", "Block C", 80, "lecture", True, False),
        ("LH-302", "Block C", 50, "lecture", True, False),
        # Labs
        ("CSE-Lab-1", "Block A", 30, "lab", True, True),
        ("CSE-Lab-2", "Block A", 30, "lab", True, True),
        ("ECE-Lab-1", "Block B", 30, "lab", True, True),
        ("ME-Lab-1", "Block C", 25, "lab", True, True),
        ("IT-Lab-1", "Block B", 30, "lab", True, True),
        # Seminar halls
        ("Seminar-1", "Block A", 100, "seminar", True, False),
        ("Seminar-2", "Block C", 80, "seminar", True, False),
    ]
    classrooms = []
    for name, building, cap, rtype, proj, lab_eq in rooms:
        c = Classroom(
            name=name,
            building=building,
            capacity=cap,
            room_type=rtype,
            has_projector=proj,
            has_lab_equipment=lab_eq,
        )
        classrooms.append(c)
    db.session.add_all(classrooms)
    db.session.commit()
    return classrooms


def seed_students(courses):
    """Create sample students."""
    first_names = [
        "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun",
        "Reyansh", "Ayaan", "Krishna", "Ishaan", "Sai",
        "Ananya", "Diya", "Myra", "Sara", "Aanya",
        "Aadhya", "Ira", "Anika", "Riya", "Kavya",
    ]
    students = []
    roll_counter = 1
    for course in courses:
        for i in range(15):  # 15 students per course
            name = random.choice(first_names) + " " + random.choice(["Sharma", "Verma", "Patel", "Kumar", "Singh"])
            s = Student(
                name=name,
                roll_number=f"{course.code}{roll_counter:03d}",
                email=f"student{roll_counter}@univ.edu",
                course_id=course.id,
                semester=5,
            )
            students.append(s)
            roll_counter += 1
    db.session.add_all(students)
    db.session.commit()
    return students


def seed_faculty_preferences(faculty_list, time_slots):
    """Generate random faculty preferences for time slots."""
    prefs = []
    for f in faculty_list:
        # Each faculty has preferences for a subset of time slots
        sample_slots = random.sample(time_slots, min(15, len(time_slots)))
        for slot in sample_slots:
            pref = FacultyPreference(
                faculty_id=f.id,
                timeslot_id=slot.id,
                preference_level=random.choice([1, 2, 3, 3, 3, 4]),  # Biased towards 'prefer'
            )
            prefs.append(pref)
    db.session.add_all(prefs)
    db.session.commit()
    return prefs


def seed_historical_data(subjects, faculty_list, classrooms):
    """Generate synthetic historical schedule data for ML training."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    history = []
    for year in ["2021-22", "2022-23", "2023-24"]:
        for s in subjects:
            course = Course.query.get(s.course_id)
            eligible_faculty = [f for f in faculty_list if s in f.subjects]
            if not eligible_faculty:
                eligible_faculty = [random.choice(faculty_list)]
            faculty = random.choice(eligible_faculty)

            for _ in range(s.hours_per_week):
                day = random.choice(days)
                period = random.randint(1, 8)
                classroom = random.choice(classrooms)
                h = ScheduleHistory(
                    academic_year=year,
                    semester=5,
                    course_id=course.id,
                    subject_id=s.id,
                    faculty_id=faculty.id,
                    classroom_id=classroom.id,
                    day=day,
                    period_number=period,
                    fitness_score=random.uniform(0.5, 1.0),
                    conflict_count=random.randint(0, 3),
                    student_satisfaction=random.uniform(3.0, 5.0),
                )
                history.append(h)
    db.session.add_all(history)
    db.session.commit()
    return history


def seed_all():
    """Run all seeders in correct order."""
    print("Seeding time slots...")
    slots = seed_time_slots()
    print(f"  Created {len(slots)} time slots")

    print("Seeding departments...")
    departments = seed_departments()
    print(f"  Created {len(departments)} departments")

    print("Seeding courses...")
    courses = seed_courses(departments)
    print(f"  Created {len(courses)} courses")

    print("Seeding subjects...")
    subjects = seed_subjects(courses)
    print(f"  Created {len(subjects)} subjects")

    print("Seeding faculty...")
    faculty_list = seed_faculty(departments, subjects)
    print(f"  Created {len(faculty_list)} faculty members")

    print("Seeding classrooms...")
    classrooms = seed_classrooms()
    print(f"  Created {len(classrooms)} classrooms")

    print("Seeding students...")
    students = seed_students(courses)
    print(f"  Created {len(students)} students")

    print("Seeding faculty preferences...")
    prefs = seed_faculty_preferences(faculty_list, slots)
    print(f"  Created {len(prefs)} preferences")

    print("Seeding historical data...")
    history = seed_historical_data(subjects, faculty_list, classrooms)
    print(f"  Created {len(history)} historical records")

    print("Database seeding complete!")
