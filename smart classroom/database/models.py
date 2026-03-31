"""
Database Models for Smart Classroom Timetable Scheduler.
Defines all SQLAlchemy ORM models and relationships.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    courses = db.relationship("Course", backref="department", lazy=True)
    faculty = db.relationship("Faculty", backref="department", lazy=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "code": self.code}


class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    total_semesters = db.Column(db.Integer, default=8)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subjects = db.relationship("Subject", backref="course", lazy=True)
    students = db.relationship("Student", backref="course", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "total_semesters": self.total_semesters,
        }


class Subject(db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    subject_type = db.Column(db.String(20), default="theory")  # theory, lab, tutorial
    hours_per_week = db.Column(db.Integer, default=3)
    requires_lab = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=5)  # 1=highest, 10=lowest
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    timetable_entries = db.relationship("TimetableEntry", backref="subject", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "course_id": self.course_id,
            "course_name": self.course.name if self.course else None,
            "semester": self.semester,
            "subject_type": self.subject_type,
            "hours_per_week": self.hours_per_week,
            "requires_lab": self.requires_lab,
            "priority": self.priority,
        }


# Association table for faculty-subject many-to-many
faculty_subjects = db.Table(
    "faculty_subjects",
    db.Column("faculty_id", db.Integer, db.ForeignKey("faculty.id"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subjects.id"), primary_key=True),
)


class Faculty(db.Model):
    __tablename__ = "faculty"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    designation = db.Column(db.String(50), default="Assistant Professor")
    max_hours_per_week = db.Column(db.Integer, default=20)
    max_hours_per_day = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subjects = db.relationship("Subject", secondary=faculty_subjects, backref="faculty_members")
    preferences = db.relationship("FacultyPreference", backref="faculty", lazy=True)
    timetable_entries = db.relationship("TimetableEntry", backref="faculty", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "designation": self.designation,
            "max_hours_per_week": self.max_hours_per_week,
            "max_hours_per_day": self.max_hours_per_day,
            "subjects": [s.name for s in self.subjects],
        }


class Classroom(db.Model):
    __tablename__ = "classrooms"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    building = db.Column(db.String(50), default="Main")
    capacity = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(20), default="lecture")  # lecture, lab, seminar
    has_projector = db.Column(db.Boolean, default=True)
    has_lab_equipment = db.Column(db.Boolean, default=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    timetable_entries = db.relationship("TimetableEntry", backref="classroom", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "building": self.building,
            "capacity": self.capacity,
            "room_type": self.room_type,
            "has_projector": self.has_projector,
            "has_lab_equipment": self.has_lab_equipment,
            "is_available": self.is_available,
        }


class TimeSlot(db.Model):
    __tablename__ = "time_slots"
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False)
    period_number = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    is_break = db.Column(db.Boolean, default=False)

    timetable_entries = db.relationship("TimetableEntry", backref="time_slot", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "day": self.day,
            "period_number": self.period_number,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "is_break": self.is_break,
        }


class TimetableEntry(db.Model):
    __tablename__ = "timetable_entries"
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=False)
    timeslot_id = db.Column(db.Integer, db.ForeignKey("time_slots.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(20), default="2024-25")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship("Course", backref="timetable_entries")

    __table_args__ = (
        db.UniqueConstraint(
            "faculty_id", "timeslot_id", "academic_year",
            name="uq_faculty_timeslot"
        ),
        db.UniqueConstraint(
            "classroom_id", "timeslot_id", "academic_year",
            name="uq_classroom_timeslot"
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject.to_dict() if self.subject else None,
            "faculty": {"id": self.faculty_id, "name": self.faculty.name} if self.faculty else None,
            "classroom": self.classroom.to_dict() if self.classroom else None,
            "time_slot": self.time_slot.to_dict() if self.time_slot else None,
            "course_id": self.course_id,
            "semester": self.semester,
            "academic_year": self.academic_year,
        }


class FacultyPreference(db.Model):
    __tablename__ = "faculty_preferences"
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)
    timeslot_id = db.Column(db.Integer, db.ForeignKey("time_slots.id"), nullable=False)
    preference_level = db.Column(db.Integer, default=3)  # 1=avoid, 2=neutral, 3=prefer, 4=strongly prefer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    time_slot = db.relationship("TimeSlot")

    def to_dict(self):
        return {
            "id": self.id,
            "faculty_id": self.faculty_id,
            "timeslot_id": self.timeslot_id,
            "preference_level": self.preference_level,
        }


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "roll_number": self.roll_number,
            "email": self.email,
            "course_id": self.course_id,
            "course_name": self.course.name if self.course else None,
            "semester": self.semester,
        }


class ScheduleHistory(db.Model):
    """Stores historical timetable data for ML training."""
    __tablename__ = "schedule_history"
    id = db.Column(db.Integer, primary_key=True)
    academic_year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    course_id = db.Column(db.Integer, nullable=False)
    subject_id = db.Column(db.Integer, nullable=False)
    faculty_id = db.Column(db.Integer, nullable=False)
    classroom_id = db.Column(db.Integer, nullable=False)
    day = db.Column(db.String(10), nullable=False)
    period_number = db.Column(db.Integer, nullable=False)
    fitness_score = db.Column(db.Float, default=0.0)
    conflict_count = db.Column(db.Integer, default=0)
    student_satisfaction = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "academic_year": self.academic_year,
            "subject_id": self.subject_id,
            "faculty_id": self.faculty_id,
            "classroom_id": self.classroom_id,
            "day": self.day,
            "period_number": self.period_number,
            "fitness_score": self.fitness_score,
        }
