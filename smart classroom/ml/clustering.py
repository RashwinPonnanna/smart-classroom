"""
K-Means Clustering for Classroom Utilization Analysis.

WHY Clustering: Identifies patterns in how classrooms are used — peak hours,
underutilized rooms, subject-room affinity. This helps the scheduler make
better room allocation decisions.

CLUSTERS IDENTIFIED:
- High-demand lecture halls (morning heavy)
- Underutilized rooms (candidates for reallocation)
- Lab-heavy time blocks
- Balanced-use rooms (ideal distribution)
"""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from collections import defaultdict
from database.models import db, TimetableEntry, Classroom, TimeSlot


class ClassroomClusterAnalyzer:
    """Analyzes classroom usage patterns using K-Means clustering."""

    def __init__(self, n_clusters=4):
        self.n_clusters = n_clusters
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.cluster_labels = {
            0: "High Demand",
            1: "Morning Heavy",
            2: "Underutilized",
            3: "Balanced Use",
        }

    def _build_usage_matrix(self, entries=None):
        """
        Build a feature matrix for each classroom based on usage patterns.

        Features per classroom:
        - total_bookings: Total number of bookings
        - morning_ratio: % of bookings in morning (periods 1-4)
        - afternoon_ratio: % of bookings in afternoon (periods 5-8)
        - avg_daily_usage: Average bookings per day
        - usage_variance: Variance in daily usage (consistency)
        - unique_subjects: Number of distinct subjects
        - lab_ratio: % of lab sessions
        """
        if entries is None:
            entries = TimetableEntry.query.filter_by(is_active=True).all()

        if not entries:
            return None, None

        classrooms = Classroom.query.all()
        room_ids = [c.id for c in classrooms]

        # Aggregate usage data per room
        room_data = defaultdict(lambda: {
            "total": 0,
            "morning": 0,
            "afternoon": 0,
            "days": defaultdict(int),
            "subjects": set(),
            "labs": 0,
        })

        for entry in entries:
            ts = entry.time_slot
            if not ts:
                continue
            rd = room_data[entry.classroom_id]
            rd["total"] += 1
            if ts.period_number <= 4:
                rd["morning"] += 1
            else:
                rd["afternoon"] += 1
            rd["days"][ts.day] += 1
            rd["subjects"].add(entry.subject_id)
            subject = entry.subject
            if subject and subject.requires_lab:
                rd["labs"] += 1

        # Build feature matrix
        X = []
        valid_room_ids = []
        for room_id in room_ids:
            rd = room_data[room_id]
            total = max(rd["total"], 1)  # Avoid division by zero
            daily_counts = [rd["days"].get(d, 0) for d in
                           ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]]

            features = [
                rd["total"],
                rd["morning"] / total,
                rd["afternoon"] / total,
                np.mean(daily_counts),
                np.var(daily_counts),
                len(rd["subjects"]),
                rd["labs"] / total,
            ]
            X.append(features)
            valid_room_ids.append(room_id)

        return np.array(X), valid_room_ids

    def fit(self, entries=None):
        """Fit the clustering model on current or provided timetable entries."""
        X, room_ids = self._build_usage_matrix(entries)

        if X is None or len(X) < self.n_clusters:
            self.is_fitted = False
            return {"status": "insufficient_data"}

        X_scaled = self.scaler.fit_transform(X)

        self.model = KMeans(
            n_clusters=min(self.n_clusters, len(X)),
            random_state=42,
            n_init=10,
        )
        labels = self.model.fit_predict(X_scaled)

        self.is_fitted = True
        self._room_clusters = dict(zip(room_ids, labels))

        return {
            "status": "fitted",
            "n_clusters": self.n_clusters,
            "rooms_analyzed": len(room_ids),
            "cluster_sizes": {
                int(i): int(np.sum(labels == i))
                for i in range(self.n_clusters)
            },
        }

    def get_room_cluster(self, classroom_id):
        """Get the cluster assignment for a specific classroom."""
        if not self.is_fitted:
            return None
        label = self._room_clusters.get(classroom_id)
        if label is not None:
            return {
                "cluster_id": int(label),
                "cluster_name": self.cluster_labels.get(label, f"Cluster {label}"),
            }
        return None

    def get_utilization_report(self):
        """Generate a utilization report grouped by cluster."""
        if not self.is_fitted:
            return {"status": "not_fitted"}

        report = {}
        for cluster_id in range(self.n_clusters):
            room_ids = [
                rid for rid, label in self._room_clusters.items()
                if label == cluster_id
            ]
            rooms = Classroom.query.filter(Classroom.id.in_(room_ids)).all() if room_ids else []
            report[self.cluster_labels.get(cluster_id, f"Cluster {cluster_id}")] = {
                "room_count": len(rooms),
                "rooms": [{"id": r.id, "name": r.name, "capacity": r.capacity, "type": r.room_type} for r in rooms],
            }
        return report

    def suggest_room(self, subject_type, student_count, period_number):
        """
        Suggest the best room based on clustering insights.

        Logic:
        - Labs -> lab rooms
        - High-demand periods -> larger rooms from balanced/high-demand clusters
        - Low-demand periods -> can use underutilized rooms
        """
        if subject_type == "lab":
            rooms = Classroom.query.filter_by(
                room_type="lab", has_lab_equipment=True, is_available=True
            ).filter(Classroom.capacity >= student_count).all()
        else:
            rooms = Classroom.query.filter(
                Classroom.room_type.in_(["lecture", "seminar"]),
                Classroom.is_available == True,
                Classroom.capacity >= student_count,
            ).all()

        if not rooms:
            return None

        # If clustering is fitted, prefer balanced-use rooms
        if self.is_fitted:
            scored = []
            for room in rooms:
                cluster = self._room_clusters.get(room.id, -1)
                # Prefer rooms that aren't overloaded
                if cluster == 2:  # Underutilized — good candidate
                    score = 3
                elif cluster == 3:  # Balanced
                    score = 2
                else:
                    score = 1
                # Capacity fit bonus (closer to need = better)
                capacity_ratio = student_count / room.capacity if room.capacity > 0 else 0
                score += capacity_ratio
                scored.append((room, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]

        # Fallback: smallest room that fits
        rooms.sort(key=lambda r: r.capacity)
        return rooms[0]
