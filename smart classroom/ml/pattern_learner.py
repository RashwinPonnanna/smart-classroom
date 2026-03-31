"""
Decision Tree Pattern Learner.

WHY Decision Trees: They learn interpretable rules from historical scheduling data,
such as "Theory classes with senior faculty perform best in morning slots" or
"Lab sessions cluster better in afternoon periods." These patterns help the GA
start with better initial populations.

DATA FLOW:
1. Extract features from historical schedules (ScheduleHistory table)
2. Train a DecisionTreeRegressor to predict quality scores
3. Use predictions to bias initial GA population toward proven patterns
"""

import numpy as np
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from database.models import db, ScheduleHistory, Subject


class PatternLearner:
    """Learns scheduling patterns from historical data using Decision Trees."""

    def __init__(self):
        self.model = None
        self.encoders = {}
        self.is_trained = False
        self.feature_names = [
            "day_encoded", "period_number", "subject_type_encoded",
            "faculty_id", "hours_per_week", "requires_lab",
        ]

    def _prepare_features(self, history_records):
        """
        Convert raw history records into feature matrix and target vector.

        Features:
        - day_encoded: Day of week as integer
        - period_number: Which period (1-8)
        - subject_type_encoded: theory=0, lab=1, tutorial=2
        - faculty_id: Faculty identifier
        - hours_per_week: Subject hours per week
        - requires_lab: Boolean -> int

        Target: fitness_score (higher = better schedule quality)
        """
        if not history_records:
            return None, None

        days_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}
        type_map = {"theory": 0, "lab": 1, "tutorial": 2}

        X = []
        y = []

        # Pre-fetch subject info
        subject_cache = {}
        for s in Subject.query.all():
            subject_cache[s.id] = s

        for record in history_records:
            subject = subject_cache.get(record.subject_id)
            if not subject:
                continue

            features = [
                days_map.get(record.day, 0),
                record.period_number,
                type_map.get(subject.subject_type, 0),
                record.faculty_id,
                subject.hours_per_week,
                1 if subject.requires_lab else 0,
            ]
            X.append(features)
            y.append(record.fitness_score)

        if not X:
            return None, None

        return np.array(X), np.array(y)

    def train(self):
        """Train the decision tree on historical schedule data."""
        history = ScheduleHistory.query.all()
        if len(history) < 10:
            print("Not enough historical data to train pattern learner.")
            self.is_trained = False
            return {"status": "insufficient_data", "records": len(history)}

        X, y = self._prepare_features(history)
        if X is None:
            self.is_trained = False
            return {"status": "feature_extraction_failed"}

        # Split for evaluation
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train decision tree with controlled depth to avoid overfitting
        self.model = DecisionTreeRegressor(
            max_depth=8,
            min_samples_split=5,
            min_samples_leaf=3,
            random_state=42,
        )
        self.model.fit(X_train, y_train)

        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)

        self.is_trained = True

        return {
            "status": "trained",
            "records_used": len(history),
            "train_r2": round(train_score, 4),
            "test_r2": round(test_score, 4),
            "feature_importances": dict(zip(
                self.feature_names,
                [round(f, 4) for f in self.model.feature_importances_],
            )),
        }

    def predict_quality(self, day, period, subject_type, faculty_id, hours_per_week, requires_lab):
        """
        Predict the quality score for a proposed schedule assignment.

        Returns:
            float: Predicted quality score (higher = better)
        """
        if not self.is_trained or self.model is None:
            return 0.5  # Neutral score if model not trained

        days_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}
        type_map = {"theory": 0, "lab": 1, "tutorial": 2}

        features = np.array([[
            days_map.get(day, 0),
            period,
            type_map.get(subject_type, 0),
            faculty_id,
            hours_per_week,
            1 if requires_lab else 0,
        ]])

        return float(self.model.predict(features)[0])

    def get_best_slots(self, subject, faculty_id, top_n=5):
        """
        Get the top N best predicted time slots for a subject-faculty pair.

        Returns:
            List of (day, period, predicted_score) tuples sorted by score desc.
        """
        if not self.is_trained:
            return []

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        predictions = []

        for day in days:
            for period in range(1, 9):
                score = self.predict_quality(
                    day, period, subject.subject_type,
                    faculty_id, subject.hours_per_week, subject.requires_lab,
                )
                predictions.append((day, period, score))

        predictions.sort(key=lambda x: x[2], reverse=True)
        return predictions[:top_n]

    def get_feature_rules(self):
        """Extract human-readable rules from the trained decision tree."""
        if not self.is_trained or self.model is None:
            return []

        tree = self.model.tree_
        rules = []

        def _extract(node, conditions):
            if tree.feature[node] == -2:  # Leaf node
                value = tree.value[node][0][0]
                if conditions:
                    rules.append({
                        "conditions": list(conditions),
                        "predicted_quality": round(value, 3),
                        "samples": tree.n_node_samples[node],
                    })
                return

            feature_name = self.feature_names[tree.feature[node]]
            threshold = tree.threshold[node]

            # Left child (<=)
            _extract(
                tree.children_left[node],
                conditions + [f"{feature_name} <= {threshold:.2f}"],
            )
            # Right child (>)
            _extract(
                tree.children_right[node],
                conditions + [f"{feature_name} > {threshold:.2f}"],
            )

        _extract(0, [])
        # Return top rules by sample count
        rules.sort(key=lambda r: r["samples"], reverse=True)
        return rules[:20]
