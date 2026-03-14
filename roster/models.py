"""
Data models for EOC Roster Generator.
Contains dataclasses for Employee, Shift, DayAssignment, and Roster.
"""

from dataclasses import dataclass, field
from datetime import date, time
from typing import List, Dict, Optional
from enum import Enum


class ShiftType(Enum):
    """Enum representing the three 8-hour shifts."""
    SHIFT_1 = 1  # 7:00 AM – 3:00 PM EST
    SHIFT_2 = 2  # 3:00 PM – 11:00 PM EST
    SHIFT_3 = 3  # 11:00 PM – 7:00 AM EST


@dataclass
class Shift:
    """Represents a work shift with time details."""
    shift_type: ShiftType
    start_time_est: time
    end_time_est: time
    start_time_ist: time
    end_time_ist: time
    
    @classmethod
    def get_all_shifts(cls) -> List['Shift']:
        """Return all three shifts with their time configurations."""
        # IST is primary timezone, EST shown for US overlap
        return [
            cls(
                shift_type=ShiftType.SHIFT_1,
                start_time_ist=time(13, 30),  # 1:30 PM IST
                end_time_ist=time(21, 30),    # 9:30 PM IST
                start_time_est=time(3, 0),    # 3:00 AM EST
                end_time_est=time(11, 0)      # 11:00 AM EST
            ),
            cls(
                shift_type=ShiftType.SHIFT_2,
                start_time_ist=time(21, 30),  # 9:30 PM IST
                end_time_ist=time(5, 30),     # 5:30 AM IST (next day)
                start_time_est=time(11, 0),   # 11:00 AM EST
                end_time_est=time(19, 0)      # 7:00 PM EST
            ),
            cls(
                shift_type=ShiftType.SHIFT_3,
                start_time_ist=time(5, 30),   # 5:30 AM IST
                end_time_ist=time(13, 30),    # 1:30 PM IST
                start_time_est=time(19, 0),   # 7:00 PM EST (prev day)
                end_time_est=time(3, 0)       # 3:00 AM EST
            )
        ]
    
    def get_display_name(self) -> str:
        """Return human-readable shift name."""
        names = {
            ShiftType.SHIFT_1: "Shift 1 (IST: 1:30 PM - 9:30 PM)",
            ShiftType.SHIFT_2: "Shift 2 (IST: 9:30 PM - 5:30 AM)", 
            ShiftType.SHIFT_3: "Shift 3 (IST: 5:30 AM - 1:30 PM)"
        }
        return names[self.shift_type]


@dataclass
class Employee:
    """Represents a team member with their attributes."""
    name: str
    seniority_rank: int  # 1 = most senior
    assigned_shift: Optional[ShiftType] = None
    leaves: List[date] = field(default_factory=list)
    days_off: List[date] = field(default_factory=list)
    # Fixed weekly pattern: maps day index (0=Mon, 6=Sun) to working (True/False)
    weekly_pattern: Dict[int, bool] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "seniority_rank": self.seniority_rank
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Employee':
        """Create Employee from dictionary."""
        return cls(
            name=data["name"],
            seniority_rank=data["seniority_rank"]
        )


@dataclass
class ShiftAssignment:
    """Represents staff assigned to a specific shift on a specific day."""
    shift_type: ShiftType
    lead: Optional[Employee] = None
    backup: Optional[Employee] = None
    members: List[Employee] = field(default_factory=list)
    
    def get_all_assigned(self) -> List[Employee]:
        """Get all employees assigned to this shift."""
        result = []
        if self.lead:
            result.append(self.lead)
        if self.backup:
            result.append(self.backup)
        result.extend(self.members)
        return result
    
    def get_staff_count(self) -> int:
        """Return total number of staff assigned."""
        return len(self.get_all_assigned())


@dataclass
class DayAssignment:
    """Represents all shift assignments for a single day."""
    date: date
    day_name: str  # Monday, Tuesday, etc.
    is_weekend: bool
    shift_1: ShiftAssignment = field(default_factory=lambda: ShiftAssignment(ShiftType.SHIFT_1))
    shift_2: ShiftAssignment = field(default_factory=lambda: ShiftAssignment(ShiftType.SHIFT_2))
    shift_3: ShiftAssignment = field(default_factory=lambda: ShiftAssignment(ShiftType.SHIFT_3))
    
    def get_shift(self, shift_type: ShiftType) -> ShiftAssignment:
        """Get shift assignment by type."""
        mapping = {
            ShiftType.SHIFT_1: self.shift_1,
            ShiftType.SHIFT_2: self.shift_2,
            ShiftType.SHIFT_3: self.shift_3
        }
        return mapping[shift_type]
    
    def get_required_staff_per_shift(self) -> int:
        """Return required staff per shift based on day type."""
        return 3 if self.is_weekend else 4


@dataclass
class RosterStatistics:
    """Statistics about the generated roster for fairness analysis."""
    total_shifts_scheduled: int = 0
    avg_working_days: float = 0.0
    avg_weekend_shifts: float = 0.0
    avg_night_shifts: float = 0.0
    min_weekend_shifts: int = 0
    max_weekend_shifts: int = 0
    min_night_shifts: int = 0
    max_night_shifts: int = 0
    all_coverage_met: bool = True
    all_leaves_accommodated: bool = True
    warnings: List[str] = field(default_factory=list)
    
    # Per-employee statistics
    employee_stats: Dict[str, dict] = field(default_factory=dict)


@dataclass
class Roster:
    """Complete roster for a month with all assignments and statistics."""
    month: int
    year: int
    employees: List[Employee]
    schedule: List[DayAssignment] = field(default_factory=list)
    statistics: Optional[RosterStatistics] = None
    
    def get_month_name(self) -> str:
        """Return the name of the month."""
        import calendar
        return calendar.month_name[self.month]
    
    def get_total_days(self) -> int:
        """Return total days in the month."""
        import calendar
        return calendar.monthrange(self.year, self.month)[1]
    
    def calculate_statistics(self) -> RosterStatistics:
        """Calculate and return roster statistics."""
        stats = RosterStatistics()
        
        # Initialize per-employee stats
        for emp in self.employees:
            stats.employee_stats[emp.name] = {
                "working_days": 0,
                "days_off": 0,
                "weekend_shifts": 0,
                "night_shifts": 0,
                "assigned_shift": emp.assigned_shift.value if emp.assigned_shift else None,
                "consecutive_off_check": True
            }
        
        # Calculate statistics from schedule
        for day in self.schedule:
            for shift_type in ShiftType:
                shift_assignment = day.get_shift(shift_type)
                for emp in shift_assignment.get_all_assigned():
                    stats.employee_stats[emp.name]["working_days"] += 1
                    stats.total_shifts_scheduled += 1
                    
                    if day.is_weekend:
                        stats.employee_stats[emp.name]["weekend_shifts"] += 1
                    
                    if shift_type == ShiftType.SHIFT_3:
                        stats.employee_stats[emp.name]["night_shifts"] += 1
        
        # Calculate averages and ranges
        working_days = [s["working_days"] for s in stats.employee_stats.values()]
        weekend_shifts = [s["weekend_shifts"] for s in stats.employee_stats.values()]
        night_shifts = [s["night_shifts"] for s in stats.employee_stats.values()]
        
        if working_days:
            stats.avg_working_days = sum(working_days) / len(working_days)
            stats.avg_weekend_shifts = sum(weekend_shifts) / len(weekend_shifts)
            stats.avg_night_shifts = sum(night_shifts) / len(night_shifts)
            stats.min_weekend_shifts = min(weekend_shifts)
            stats.max_weekend_shifts = max(weekend_shifts)
            stats.min_night_shifts = min(night_shifts)
            stats.max_night_shifts = max(night_shifts)
        
        # Set days off
        for emp in self.employees:
            total_days = self.get_total_days()
            working = stats.employee_stats[emp.name]["working_days"]
            stats.employee_stats[emp.name]["days_off"] = total_days - working
        
        self.statistics = stats
        return stats
