import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "smart-timetable-secret-key-2024")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'timetable.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Timetable generation settings
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    PERIODS_PER_DAY = 8
    PERIOD_START_HOUR = 9  # 9 AM
    PERIOD_DURATION_MINUTES = 50
    BREAK_AFTER_PERIOD = 4  # Lunch break after 4th period
    BREAK_DURATION_MINUTES = 40

    # Genetic Algorithm settings
    GA_POPULATION_SIZE = 100
    GA_GENERATIONS = 200
    GA_CROSSOVER_PROB = 0.8
    GA_MUTATION_PROB = 0.2
    GA_TOURNAMENT_SIZE = 5

    # Constraint weights
    WEIGHT_HARD_CONFLICT = 1000
    WEIGHT_CAPACITY = 500
    WEIGHT_FACULTY_PREF = 50
    WEIGHT_WORKLOAD_BALANCE = 30
    WEIGHT_CONSECUTIVE = 20
    WEIGHT_LUNCH_BREAK = 100
