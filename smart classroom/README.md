# Smart Classroom Timetable Scheduler Using Machine Learning

A fully functional intelligent academic timetable scheduling system that automatically generates conflict-free, optimized class schedules using machine learning and constraint-based optimization.

## Quick Start

### Installation
```bash
cd yoge
pip install -r requirements.txt
```

### Run the Application
```bash
python app.py
```

The application will:
- Initialize SQLite database (auto-creates if missing)
- Seed sample data (4 departments, 28 subjects, 16 faculty, 15 classrooms, 60 students)
- Start Flask development server on `http://127.0.0.1:5000`

### Access Points
| Role | URL |
|------|-----|
| **Admin Dashboard** | http://127.0.0.1:5000/admin/dashboard |
| **Admin Timetable** | http://127.0.0.1:5000/admin/timetable |
| **Faculty View** | http://127.0.0.1:5000/faculty/schedule |
| **Student View** | http://127.0.0.1:5000/student/timetable |
| **REST API** | http://127.0.0.1:5000/api/analytics |

## Architecture

### Tech Stack
- **Backend**: Python Flask + SQLAlchemy ORM
- **Database**: SQLite (10 tables, ~320 records)
- **ML**: DEAP (Genetic Algorithm), scikit-learn (Decision Trees, K-Means)
- **Frontend**: HTML5 + Bootstrap 5 + Chart.js
- **Python**: 3.8+ required

### Project Structure
```
yoge/
├── app.py                         # Flask entry point
├── config.py                      # Configuration settings
├── requirements.txt               # Dependencies
├── database/
│   ├── models.py                  # SQLAlchemy models (10 tables)
│   ├── schema.sql                 # Raw SQL documentation
│   └── seed_data.py               # Sample data generation
├── ml/
│   ├── constraint_solver.py       # CSP constraint engine
│   ├── genetic_algorithm.py       # GA optimizer (DEAP)
│   ├── pattern_learner.py         # Decision Tree learning
│   ├── clustering.py              # K-Means analysis
│   └── pipeline.py                # ML orchestrator
├── services/
│   ├── timetable_generator.py     # Core generation logic
│   ├── conflict_resolver.py       # Conflict detection/resolution
│   └── analytics.py               # Reports & statistics
├── routes/
│   ├── admin.py                   # Admin endpoints
│   ├── faculty.py                 # Faculty endpoints
│   ├── student.py                 # Student endpoints
│   └── api.py                     # REST API endpoints
├── templates/
│   ├── base.html                  # Base layout
│   ├── admin/dashboard.html       # Admin dashboard
│   ├── admin/manage.html          # CRUD management
│   ├── admin/timetable.html       # Timetable view
│   ├── faculty/schedule.html      # Faculty schedule
│   └── student/timetable.html     # Student timetable
├── static/
│   ├── css/style.css              # Custom styles
│   └── js/main.js                 # Frontend logic
└── docs/
    └── report.md                  # Full project report
```

## ML System Overview

### Hybrid Intelligent System

**Four ML Components Working Together:**

1. **Constraint Satisfaction Problem (CSP) Engine**
   - Enforces hard constraints (no double-booking, capacity limits)
   - Evaluates soft constraints (preferences, workload balance)
   - Filters solution space to guarantee feasibility

2. **Genetic Algorithm Optimizer** (DEAP library)
   - Population: 100 individuals
   - Generations: 200 (with early stopping)
   - Operations: Tournament selection, two-point crossover, swap mutation
   - Fitness: Weighted constraint violation scoring

3. **Decision Tree Pattern Learner** (scikit-learn)
   - Trains on historical schedule data
   - Predicts quality scores for proposed assignments
   - Learns patterns like "morning slots best for theory classes"

4. **K-Means Clustering** (scikit-learn)
   - Identifies room usage patterns
   - Finds underutilized vs. overloaded spaces
   - Guides better room allocation

### Data Flow
```
Input: Departments, Courses, Subjects, Faculty, Classrooms, Preferences
  ↓
[Pattern Learner] Train on historical data
  ↓
[CSP Engine] Define hard constraints
  ↓
[Genetic Algorithm] Evolve 100 populations over 200 generations
  ↓
[Constraint Validation] Verify zero violations
  ↓
[Clustering] Analyze room usage patterns
  ↓
Output: Conflict-free timetable + Analytics
  ↓
[Database] Save to schedule_history for future ML training
```

## Core Features

### Admin Module
- Dashboard with stats cards and charts
- CRUD management for all entities
- One-click timetable generation with ML
- Conflict detection and auto-resolution
- Analytics: room utilization, faculty workload, time distribution

### Faculty Module
- View personal weekly schedule
- Set time slot preferences (Avoid/Neutral/Prefer/Strongly Prefer)
- Dynamic rescheduling requests

### Student Module
- View course-specific timetable
- See classroom details and locations
- Browse all available rooms

### REST API
- `/api/analytics` - Dashboard statistics
- `/api/timetable` - Retrieve schedules (filterable)
- `/api/timetable/generate` - Trigger ML generation
- `/api/conflicts` - Detect scheduling conflicts
- `/api/departments`, `/api/courses`, `/api/faculty`, etc.

## Key Algorithms

### Genetic Algorithm Fitness Function
```
Total Penalty =
  1000 × (hard conflicts)              // Never allow violations
  + 500 × (capacity violations)        // Room too small
  + 100 × (lunch break violations)     // 12:30-13:10 protected
  + 50 × (preference mismatches)       // Faculty preferences
  + 30 × (workload variance)           // Balance across faculty
  + 20 × (excessive consecutive)       // Max 3 consecutive classes
```

### CSP Hard Constraints
- No faculty double-booking at same time slot
- No classroom double-booking at same time slot
- No course-semester overlap at same time slot
- Faculty daily/weekly hour limits respected
- Lab subjects assigned to lab rooms only

### CSP Soft Constraints (Minimized)
- Faculty time slot preferences
- Maximum consecutive classes (limit: 3)
- Lunch break preservation
- Faculty workload balance

## Sample Output

**Generated Timetable:**
- **84 entries** across 4 departments
- **21 entries per department** (balanced)
- **0 hard-constraint violations** (guaranteed feasible)
- **0 conflicts detected**

**Example Schedule:**
```
Monday, Period 1 (09:00-09:50)
├── Manufacturing Processes | Dr. Arun Joshi | LH-203 | Theory
├── Microprocessors | Prof. Meera Patel | LH-101 | Theory
├── Web Technologies | Dr. Amit Tiwari | Seminar-2 | Theory
└── [Other entries]

Friday, Period 5 (13:10-14:00) [After Lunch]
├── Computer Networks | Prof. Sneha Gupta | LH-202 | Theory
├── Communication Systems | Dr. Suresh Reddy | LH-203 | Theory
├── Fluid Mechanics | Prof. Deepa Nair | LH-103 | Theory
├── Web Lab | Prof. Ritu Saxena | IT-Lab-1 | Lab
└── [Other entries]
```

## Database Schema

### 10 Core Tables
1. **departments** - Academic departments (CSE, ECE, ME, IT)
2. **courses** - Degree programs
3. **subjects** - Course subjects (theory/lab/tutorial)
4. **faculty** - Teaching staff with constraints
5. **faculty_subjects** - Many-to-many mapping
6. **classrooms** - Rooms, labs, seminar halls
7. **time_slots** - 40 weekly periods (8/day × 5 days)
8. **timetable_entries** - Generated schedule (unique constraints on faculty-timeslot, classroom-timeslot)
9. **faculty_preferences** - Time slot preferences
10. **schedule_history** - Historical data for ML training

## Configuration

Edit `config.py` to customize:
```python
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS_PER_DAY = 8
PERIOD_START_HOUR = 9  # 9 AM
PERIOD_DURATION_MINUTES = 50
BREAK_AFTER_PERIOD = 4  # Lunch after period 4
BREAK_DURATION_MINUTES = 40

# Genetic Algorithm Settings
GA_POPULATION_SIZE = 100
GA_GENERATIONS = 200
GA_CROSSOVER_PROB = 0.8
GA_MUTATION_PROB = 0.2
GA_TOURNAMENT_SIZE = 5

# Constraint Weights
WEIGHT_HARD_CONFLICT = 1000
WEIGHT_CAPACITY = 500
WEIGHT_FACULTY_PREF = 50
WEIGHT_WORKLOAD_BALANCE = 30
WEIGHT_CONSECUTIVE = 20
WEIGHT_LUNCH_BREAK = 100
```

## Conflict Resolution

The system provides three levels of conflict handling:

1. **Prevention**: CSP filters invalid assignments during generation
2. **Detection**: Post-generation scan identifies remaining conflicts
3. **Resolution**:
   - Faculty double-booking → Suggest alternative free time slots
   - Room double-booking → Suggest alternative free rooms
   - Capacity violation → Suggest larger available rooms

## Future Enhancements

- Multi-Objective Optimization (NSGA-II) for Pareto-optimal solutions
- Reinforcement Learning for adaptive scheduling policies
- Real-time WebSocket notifications for schedule changes
- Mobile app (React Native/Flutter)
- Exam scheduling extension
- Integration with Learning Management Systems
- Multi-campus support
- Cloud deployment (AWS/Azure)

## Dependencies

See `requirements.txt`:
- Flask 3.0.0
- Flask-SQLAlchemy 3.1.1
- SQLAlchemy 2.0.48
- scikit-learn 1.8.0
- DEAP 1.4.1
- NumPy 2.4.3
- SciPy 1.17.1

## License

Educational project for academic use.

## Documentation

Full project report available in `docs/report.md` with:
- Abstract, Introduction, Literature Survey
- System Design & Architecture
- Algorithm Implementation Details
- Results & Performance Metrics
- Conclusions & Future Work
