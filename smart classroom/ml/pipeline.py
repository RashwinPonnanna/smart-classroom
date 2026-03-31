"""
ML Pipeline Orchestrator.

Coordinates all ML components into a unified timetable generation pipeline:

DATA FLOW:
1. Pattern Learner trains on historical data → learns slot quality predictions
2. Constraint Solver defines hard/soft constraints → provides fitness function
3. Genetic Algorithm creates and evolves populations → finds optimal schedule
4. Clustering analyzes room usage → provides allocation insights

INTERACTION:
- Pattern Learner biases GA's initial population toward proven patterns
- Constraint Solver provides the fitness function for GA evaluation
- GA evolves solutions, constraint solver scores them
- After generation, Clustering analyzes the result for future improvement
"""

from ml.constraint_solver import ConstraintSolver
from ml.genetic_algorithm import TimetableGA
from ml.pattern_learner import PatternLearner
from ml.clustering import ClassroomClusterAnalyzer
from database.models import db, ScheduleHistory


class MLPipeline:
    """Orchestrates the full ML pipeline for timetable generation."""

    def __init__(self, config):
        self.config = config
        self.constraint_solver = ConstraintSolver(config)
        self.pattern_learner = PatternLearner()
        self.clustering = ClassroomClusterAnalyzer(n_clusters=4)
        self.ga = TimetableGA(config, self.constraint_solver)

    def train_models(self):
        """Train all ML models on available data."""
        results = {}

        # Step 1: Train pattern learner on historical data
        results["pattern_learner"] = self.pattern_learner.train()

        # Step 2: Fit clustering on existing timetable
        results["clustering"] = self.clustering.fit()

        return results

    def generate_timetable(self, course_id=None, semester=None, callback=None):
        """
        Full pipeline execution for timetable generation.

        Steps:
        1. Train pattern learner (if historical data available)
        2. Run GA optimization with constraint-based fitness
        3. Validate result against hard constraints
        4. Update clustering model with new timetable
        5. Save to history for future learning

        Args:
            course_id: Generate for specific course (None = all)
            semester: Generate for specific semester (None = all)
            callback: Progress callback function

        Returns:
            dict with timetable, fitness, ml_insights, and violations
        """
        result = {
            "timetable": [],
            "fitness": 0,
            "ml_insights": {},
            "violations": [],
            "stats": {},
        }

        # Step 1: Train pattern learner
        if callback:
            callback("training", "Training pattern learner...")
        pt_result = self.pattern_learner.train()
        result["ml_insights"]["pattern_learner"] = pt_result

        # Step 2: Get pattern learner suggestions (for reporting)
        if self.pattern_learner.is_trained:
            rules = self.pattern_learner.get_feature_rules()
            result["ml_insights"]["learned_rules"] = rules[:5]

        # Step 3: Run genetic algorithm
        if callback:
            callback("optimizing", "Running genetic algorithm...")

        self.constraint_solver.reset_cache()
        ga_result = self.ga.optimize(course_id, semester, callback=None)

        result["timetable"] = ga_result["timetable"]
        result["fitness"] = ga_result["fitness"]
        result["stats"] = ga_result["stats"]
        result["stats"]["generations_run"] = ga_result.get("generations_run", 0)

        # Step 4: Validate hard constraints
        if callback:
            callback("validating", "Checking constraints...")
        violations = self.constraint_solver.check_hard_constraints(ga_result["timetable"])
        result["violations"] = violations

        # Step 5: Update clustering
        if callback:
            callback("analyzing", "Analyzing room utilization...")
        cluster_result = self.clustering.fit()
        result["ml_insights"]["clustering"] = cluster_result

        if self.clustering.is_fitted:
            result["ml_insights"]["utilization_report"] = self.clustering.get_utilization_report()

        # Step 6: Save to history
        self._save_to_history(ga_result["timetable"], ga_result["fitness"])

        # Cleanup GA toolbox registrations
        self.ga.cleanup()

        return result

    def _save_to_history(self, timetable, fitness_score):
        """Save generated timetable to history for future ML training."""
        for gene in timetable:
            record = ScheduleHistory(
                academic_year="2024-25",
                semester=gene.get("semester", 5),
                course_id=gene.get("course_id", 0),
                subject_id=gene["subject_id"],
                faculty_id=gene["faculty_id"],
                classroom_id=gene["classroom_id"],
                day=gene["day"],
                period_number=gene["period"],
                fitness_score=fitness_score,
                conflict_count=0,
                student_satisfaction=0.0,
            )
            db.session.add(record)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    def get_slot_recommendation(self, subject, faculty_id):
        """Get ML-powered slot recommendations for manual scheduling."""
        recommendations = []

        if self.pattern_learner.is_trained:
            best_slots = self.pattern_learner.get_best_slots(subject, faculty_id, top_n=5)
            for day, period, score in best_slots:
                recommendations.append({
                    "day": day,
                    "period": period,
                    "predicted_quality": round(score, 3),
                    "source": "pattern_learner",
                })

        return recommendations

    def get_room_recommendation(self, subject_type, student_count, period_number):
        """Get clustering-based room recommendation."""
        room = self.clustering.suggest_room(subject_type, student_count, period_number)
        if room:
            cluster = self.clustering.get_room_cluster(room.id)
            return {
                "room": room.to_dict(),
                "cluster": cluster,
            }
        return None
