"""
Genetic Algorithm for Timetable Optimization using DEAP.

WHY GA: Timetable scheduling is an NP-hard combinatorial optimization problem.
GAs excel at exploring large solution spaces and finding near-optimal solutions
through evolutionary operations (selection, crossover, mutation).

CHROMOSOME DESIGN:
- Each chromosome = a complete timetable (list of gene dicts)
- Each gene = one class assignment {subject_id, faculty_id, classroom_id, timeslot_id, ...}
- Fitness = weighted penalty score (lower = better)

OPERATIONS:
- Selection: Tournament selection (picks best from random subset)
- Crossover: Two-point crossover on gene arrays
- Mutation: Random swap of faculty/room/timeslot for a gene
"""

import random
import copy
from deap import base, creator, tools, algorithms
from database.models import db, Subject, Faculty, Classroom, TimeSlot, Course


class TimetableGA:
    """Genetic Algorithm optimizer for timetable generation."""

    def __init__(self, config, constraint_solver):
        self.config = config
        self.solver = constraint_solver
        self.subjects = []
        self.faculty_map = {}
        self.room_map = {}
        self.timeslots = []
        self._setup_deap()

    def _setup_deap(self):
        """Initialize DEAP framework."""
        # Minimize fitness (penalty score)
        if not hasattr(creator, "FitnessMin"):
            creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
        if not hasattr(creator, "Individual"):
            creator.create("Individual", list, fitness=creator.FitnessMin)

        self.toolbox = base.Toolbox()

    def _load_data(self, course_id=None, semester=None):
        """Load subjects, faculty, rooms, and timeslots from database."""
        query = Subject.query
        if course_id:
            query = query.filter_by(course_id=course_id)
        if semester:
            query = query.filter_by(semester=semester)
        self.subjects = query.all()

        # Build faculty map: subject_id -> [faculty]
        self.faculty_map = {}
        for s in self.subjects:
            eligible = list(s.faculty_members)
            if not eligible:
                dept_id = s.course.department_id
                eligible = Faculty.query.filter_by(department_id=dept_id).all()
            self.faculty_map[s.id] = eligible

        # Build room map by type
        self.room_map = {
            "lecture": Classroom.query.filter(
                Classroom.room_type.in_(["lecture", "seminar"]),
                Classroom.is_available == True,
            ).all(),
            "lab": Classroom.query.filter_by(
                room_type="lab", has_lab_equipment=True, is_available=True
            ).all(),
        }

        self.timeslots = TimeSlot.query.filter_by(is_break=False).all()

    def _create_random_gene(self, subject):
        """Create a random valid assignment for a subject."""
        faculty_list = self.faculty_map.get(subject.id, [])
        if not faculty_list:
            return None
        faculty = random.choice(faculty_list)

        room_type = "lab" if subject.requires_lab else "lecture"
        rooms = self.room_map.get(room_type, [])
        if not rooms:
            return None
        room = random.choice(rooms)

        ts = random.choice(self.timeslots)

        return {
            "subject_id": subject.id,
            "subject_name": subject.name,
            "faculty_id": faculty.id,
            "faculty_name": faculty.name,
            "classroom_id": room.id,
            "classroom_name": room.name,
            "timeslot_id": ts.id,
            "course_id": subject.course_id,
            "semester": subject.semester,
            "day": ts.day,
            "period": ts.period_number,
            "start_time": ts.start_time,
            "end_time": ts.end_time,
        }

    def _create_individual(self):
        """Create one random timetable (individual/chromosome)."""
        genes = []
        for subject in self.subjects:
            # Create assignments for each hour the subject needs per week
            for _ in range(subject.hours_per_week):
                gene = self._create_random_gene(subject)
                if gene:
                    genes.append(gene)
        return creator.Individual(genes)

    def _mutate(self, individual):
        """
        Mutation operator: randomly reassign faculty, room, or timeslot
        for a subset of genes.
        """
        for i in range(len(individual)):
            if random.random() < 0.1:  # 10% chance per gene
                gene = individual[i]
                mutation_type = random.choice(["timeslot", "room", "faculty"])

                if mutation_type == "timeslot":
                    ts = random.choice(self.timeslots)
                    gene["timeslot_id"] = ts.id
                    gene["day"] = ts.day
                    gene["period"] = ts.period_number
                    gene["start_time"] = ts.start_time
                    gene["end_time"] = ts.end_time

                elif mutation_type == "room":
                    subject = Subject.query.get(gene["subject_id"])
                    room_type = "lab" if subject and subject.requires_lab else "lecture"
                    rooms = self.room_map.get(room_type, [])
                    if rooms:
                        room = random.choice(rooms)
                        gene["classroom_id"] = room.id
                        gene["classroom_name"] = room.name

                elif mutation_type == "faculty":
                    fac_list = self.faculty_map.get(gene["subject_id"], [])
                    if fac_list:
                        fac = random.choice(fac_list)
                        gene["faculty_id"] = fac.id
                        gene["faculty_name"] = fac.name

        return (individual,)

    def _crossover(self, ind1, ind2):
        """Two-point crossover between two timetables."""
        size = min(len(ind1), len(ind2))
        if size < 3:
            return ind1, ind2

        pt1 = random.randint(1, size - 2)
        pt2 = random.randint(pt1, size - 1)

        # Swap genes between crossover points
        new1 = creator.Individual(ind1[:pt1] + copy.deepcopy(ind2[pt1:pt2]) + ind1[pt2:])
        new2 = creator.Individual(ind2[:pt1] + copy.deepcopy(ind1[pt1:pt2]) + ind2[pt2:])
        return new1, new2

    def optimize(self, course_id=None, semester=None, callback=None):
        """
        Run the genetic algorithm to find the optimal timetable.

        Args:
            course_id: Optional filter for specific course
            semester: Optional filter for specific semester
            callback: Optional function called each generation with (gen, best_fitness)

        Returns:
            dict with 'timetable' (best chromosome), 'fitness', 'stats'
        """
        self._load_data(course_id, semester)

        if not self.subjects:
            return {"timetable": [], "fitness": 0, "stats": {}}

        # Register GA operations
        self.toolbox.register("individual", self._create_individual)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("evaluate", self.solver.evaluate_fitness)
        self.toolbox.register("mate", self._crossover)
        self.toolbox.register("mutate", self._mutate)
        self.toolbox.register("select", tools.selTournament, tournsize=self.config.GA_TOURNAMENT_SIZE)

        # Create initial population
        pop_size = self.config.GA_POPULATION_SIZE
        population = self.toolbox.population(n=pop_size)

        # Evaluate initial population
        for ind in population:
            ind.fitness.values = self.toolbox.evaluate(ind)

        # Statistics
        stats = tools.Statistics(lambda ind: ind.fitness.values[0])
        stats.register("min", min)
        stats.register("avg", lambda x: sum(x) / len(x))

        # Hall of fame (keeps best individual)
        hof = tools.HallOfFame(1)

        # Evolution loop
        generations = self.config.GA_GENERATIONS
        cx_prob = self.config.GA_CROSSOVER_PROB
        mut_prob = self.config.GA_MUTATION_PROB

        logbook = tools.Logbook()

        for gen in range(generations):
            # Selection
            offspring = self.toolbox.select(population, len(population))
            offspring = list(map(copy.deepcopy, offspring))

            # Crossover
            for i in range(0, len(offspring) - 1, 2):
                if random.random() < cx_prob:
                    offspring[i], offspring[i + 1] = self.toolbox.mate(offspring[i], offspring[i + 1])
                    del offspring[i].fitness.values
                    del offspring[i + 1].fitness.values

            # Mutation
            for i in range(len(offspring)):
                if random.random() < mut_prob:
                    self.toolbox.mutate(offspring[i])
                    del offspring[i].fitness.values

            # Evaluate changed individuals
            invalid = [ind for ind in offspring if not ind.fitness.valid]
            for ind in invalid:
                ind.fitness.values = self.toolbox.evaluate(ind)

            # Replace population
            population[:] = offspring
            hof.update(population)

            record = stats.compile(population)
            logbook.record(gen=gen, **record)

            if callback:
                callback(gen, record["min"])

            # Early stopping if perfect solution found
            if record["min"] == 0:
                break

        best = hof[0]
        best_fitness = best.fitness.values[0]

        return {
            "timetable": list(best),
            "fitness": best_fitness,
            "generations_run": gen + 1,
            "stats": {
                "final_min": logbook[-1]["min"],
                "final_avg": logbook[-1]["avg"],
                "improvement": logbook[0]["min"] - logbook[-1]["min"] if len(logbook) > 1 else 0,
            },
        }

    def cleanup(self):
        """Unregister toolbox functions for reuse."""
        for name in ["individual", "population", "evaluate", "mate", "mutate", "select"]:
            try:
                self.toolbox.unregister(name)
            except Exception:
                pass
