"""
Analytics and Reporting Service.

Provides insights on:
- Classroom utilization rates
- Faculty workload distribution
- Conflict statistics
- Schedule quality metrics
"""

from collections import defaultdict
from database.models import (
    db, TimetableEntry, Faculty, Classroom, TimeSlot, Subject, Student, Course,
    Department,
)


class AnalyticsService:
    """Generates analytics and reports for the timetable system."""

    def get_dashboard_stats(self, academic_year="2024-25"):
        """Get high-level dashboard statistics."""
        entries = TimetableEntry.query.filter_by(
            academic_year=academic_year, is_active=True
        ).count()

        return {
            "total_entries": entries,
            "total_faculty": Faculty.query.count(),
            "total_classrooms": Classroom.query.count(),
            "total_subjects": Subject.query.count(),
            "total_students": Student.query.count(),
            "total_departments": Department.query.count(),
            "total_courses": Course.query.count(),
        }

    def get_room_utilization(self, academic_year="2024-25"):
        """
        Calculate utilization rate for each classroom.
        Utilization = (booked slots / total available slots) * 100
        """
        total_slots = TimeSlot.query.filter_by(is_break=False).count()
        classrooms = Classroom.query.filter_by(is_available=True).all()

        utilization = []
        for room in classrooms:
            booked = TimetableEntry.query.filter_by(
                classroom_id=room.id, academic_year=academic_year, is_active=True
            ).count()
            rate = (booked / total_slots * 100) if total_slots > 0 else 0
            utilization.append({
                "room_id": room.id,
                "room_name": room.name,
                "building": room.building,
                "capacity": room.capacity,
                "room_type": room.room_type,
                "booked_slots": booked,
                "total_slots": total_slots,
                "utilization_rate": round(rate, 1),
            })

        utilization.sort(key=lambda x: x["utilization_rate"], reverse=True)
        return utilization

    def get_faculty_workload(self, academic_year="2024-25"):
        """
        Calculate workload distribution for each faculty member.
        """
        faculty_list = Faculty.query.all()
        workload = []

        for f in faculty_list:
            entries = TimetableEntry.query.filter_by(
                faculty_id=f.id, academic_year=academic_year, is_active=True
            ).all()

            # Count hours per day
            daily = defaultdict(int)
            for e in entries:
                ts = e.time_slot
                if ts:
                    daily[ts.day] += 1

            total_hours = len(entries)
            max_daily = max(daily.values()) if daily else 0
            days_active = len(daily)

            workload.append({
                "faculty_id": f.id,
                "faculty_name": f.name,
                "department": f.department.name if f.department else "N/A",
                "designation": f.designation,
                "total_hours": total_hours,
                "max_hours_per_week": f.max_hours_per_week,
                "utilization": round(total_hours / f.max_hours_per_week * 100, 1) if f.max_hours_per_week else 0,
                "max_daily_hours": max_daily,
                "days_active": days_active,
                "daily_breakdown": dict(daily),
            })

        workload.sort(key=lambda x: x["utilization"], reverse=True)
        return workload

    def get_department_summary(self, academic_year="2024-25"):
        """Get timetable summary per department."""
        departments = Department.query.all()
        summary = []

        for dept in departments:
            courses = Course.query.filter_by(department_id=dept.id).all()
            course_ids = [c.id for c in courses]

            entries = TimetableEntry.query.filter(
                TimetableEntry.course_id.in_(course_ids),
                TimetableEntry.academic_year == academic_year,
                TimetableEntry.is_active == True,
            ).count()

            faculty_count = Faculty.query.filter_by(department_id=dept.id).count()
            subject_count = Subject.query.filter(
                Subject.course_id.in_(course_ids)
            ).count()

            summary.append({
                "department_id": dept.id,
                "department_name": dept.name,
                "department_code": dept.code,
                "courses": len(courses),
                "faculty_count": faculty_count,
                "subject_count": subject_count,
                "timetable_entries": entries,
            })

        return summary

    def get_time_distribution(self, academic_year="2024-25"):
        """
        Analyze how classes are distributed across time slots.
        Returns counts per day and per period.
        """
        entries = TimetableEntry.query.filter_by(
            academic_year=academic_year, is_active=True
        ).all()

        day_counts = defaultdict(int)
        period_counts = defaultdict(int)
        day_period = defaultdict(int)

        for e in entries:
            ts = e.time_slot
            if ts:
                day_counts[ts.day] += 1
                period_counts[ts.period_number] += 1
                day_period[(ts.day, ts.period_number)] += 1

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

        return {
            "by_day": {d: day_counts.get(d, 0) for d in days},
            "by_period": {p: period_counts.get(p, 0) for p in range(1, 9)},
            "heatmap": {
                f"{d}-{p}": day_period.get((d, p), 0)
                for d in days for p in range(1, 9)
            },
        }
