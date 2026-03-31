-- ============================================================
-- Smart Classroom Timetable Scheduler - Database Schema
-- Database: SQLite (compatible with SQL Server syntax)
-- ============================================================

-- Departments table
CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Courses table
CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    department_id INTEGER NOT NULL,
    total_semesters INTEGER DEFAULT 8,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- Subjects table
CREATE TABLE subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    course_id INTEGER NOT NULL,
    semester INTEGER NOT NULL,
    subject_type VARCHAR(20) DEFAULT 'theory',  -- theory, lab, tutorial
    hours_per_week INTEGER DEFAULT 3,
    requires_lab BOOLEAN DEFAULT 0,
    priority INTEGER DEFAULT 5,                  -- 1=highest, 10=lowest
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id)
);

-- Faculty table
CREATE TABLE faculty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    department_id INTEGER NOT NULL,
    designation VARCHAR(50) DEFAULT 'Assistant Professor',
    max_hours_per_week INTEGER DEFAULT 20,
    max_hours_per_day INTEGER DEFAULT 5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- Faculty-Subject mapping (many-to-many)
CREATE TABLE faculty_subjects (
    faculty_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    PRIMARY KEY (faculty_id, subject_id),
    FOREIGN KEY (faculty_id) REFERENCES faculty(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);

-- Classrooms table
CREATE TABLE classrooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,
    building VARCHAR(50) DEFAULT 'Main',
    capacity INTEGER NOT NULL,
    room_type VARCHAR(20) DEFAULT 'lecture',     -- lecture, lab, seminar
    has_projector BOOLEAN DEFAULT 1,
    has_lab_equipment BOOLEAN DEFAULT 0,
    is_available BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Time slots table
CREATE TABLE time_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day VARCHAR(10) NOT NULL,
    period_number INTEGER NOT NULL,
    start_time VARCHAR(10) NOT NULL,
    end_time VARCHAR(10) NOT NULL,
    is_break BOOLEAN DEFAULT 0
);

-- Timetable entries (the generated schedule)
CREATE TABLE timetable_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    faculty_id INTEGER NOT NULL,
    classroom_id INTEGER NOT NULL,
    timeslot_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    semester INTEGER NOT NULL,
    academic_year VARCHAR(20) DEFAULT '2024-25',
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (faculty_id) REFERENCES faculty(id),
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id),
    FOREIGN KEY (timeslot_id) REFERENCES time_slots(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE (faculty_id, timeslot_id, academic_year),
    UNIQUE (classroom_id, timeslot_id, academic_year)
);

-- Faculty preferences
CREATE TABLE faculty_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id INTEGER NOT NULL,
    timeslot_id INTEGER NOT NULL,
    preference_level INTEGER DEFAULT 3,          -- 1=avoid, 2=neutral, 3=prefer, 4=strongly prefer
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id),
    FOREIGN KEY (timeslot_id) REFERENCES time_slots(id)
);

-- Students table
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    roll_number VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    course_id INTEGER NOT NULL,
    semester INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id)
);

-- Schedule history (for ML training)
CREATE TABLE schedule_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    academic_year VARCHAR(20) NOT NULL,
    semester INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    faculty_id INTEGER NOT NULL,
    classroom_id INTEGER NOT NULL,
    day VARCHAR(10) NOT NULL,
    period_number INTEGER NOT NULL,
    fitness_score REAL DEFAULT 0.0,
    conflict_count INTEGER DEFAULT 0,
    student_satisfaction REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
