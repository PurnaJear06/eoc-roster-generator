"""
Core scheduling algorithm for EOC Roster Generator.
Uses OR-Tools CP-SAT solver for constraint satisfaction optimization.
"""

import calendar
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from ortools.sat.python import cp_model

from roster.models import (
    Employee, ShiftType, Shift, ShiftAssignment, 
    DayAssignment, Roster, RosterStatistics
)


class RosterScheduler:
    """Generates optimized monthly rosters using constraint satisfaction."""
    
    def __init__(self, employees: List[Employee], month: int, year: int):
        """Initialize scheduler with team and target month."""
        self.employees = sorted(employees, key=lambda e: e.seniority_rank)
        self.month = month
        self.year = year
        
        # Generate list of dates for the month
        self.num_days = calendar.monthrange(year, month)[1]
        self.dates = [
            date(year, month, day) for day in range(1, self.num_days + 1)
        ]
        
        # Shift types
        self.shifts = [ShiftType.SHIFT_1, ShiftType.SHIFT_2, ShiftType.SHIFT_3]
        
        # Staffing requirements
        self.weekday_staff = 4  # Per shift
        self.weekend_staff = 3  # Per shift
        
        # Track leaves by employee name
        self.leaves: Dict[str, List[date]] = defaultdict(list)
        for emp in self.employees:
            self.leaves[emp.name] = emp.leaves.copy()
    
    def set_leaves(self, employee_name: str, leave_dates: List[date]):
        """Set leave dates for an employee."""
        self.leaves[employee_name] = leave_dates
        # Update employee object too
        for emp in self.employees:
            if emp.name == employee_name:
                emp.leaves = leave_dates
                break
    
    def _is_weekend(self, d: date) -> bool:
        """Check if a date is a weekend (Saturday or Sunday)."""
        return d.weekday() >= 5
    
    def _get_required_staff(self, d: date) -> int:
        """Get required staff per shift for a given date."""
        return self.weekend_staff if self._is_weekend(d) else self.weekday_staff
    
    def _get_day_name(self, d: date) -> str:
        """Get day name for a date."""
        return calendar.day_name[d.weekday()]
    
    def validate_coverage(self) -> Tuple[bool, List[str]]:
        """Validate that we have enough staff to cover all shifts."""
        errors = []
        
        for d in self.dates:
            required_total = self._get_required_staff(d) * 3  # 3 shifts
            
            # Count available employees (not on leave)
            available = sum(
                1 for emp in self.employees 
                if d not in self.leaves[emp.name]
            )
            
            if available < required_total:
                errors.append(
                    f"Cannot meet staffing on {d.strftime('%b %d')}: "
                    f"Required {required_total}, Available {available}"
                )
        
        return (len(errors) == 0, errors)
    
    def generate(self) -> Optional[Roster]:
        """Generate the optimized roster using CP-SAT solver."""
        
        # First validate we have enough coverage
        valid, errors = self.validate_coverage()
        if not valid:
            print("Coverage validation failed:")
            for err in errors:
                print(f"  - {err}")
            return None
        
        model = cp_model.CpModel()
        
        num_employees = len(self.employees)
        num_shifts = len(self.shifts)
        num_days = len(self.dates)
        
        # Decision variables
        # shift_assignment[e] = which shift employee e is assigned to for the month (0, 1, 2)
        shift_assignment = {}
        for e in range(num_employees):
            shift_assignment[e] = model.NewIntVar(0, num_shifts - 1, f'shift_emp_{e}')
        
        # works[e, d] = 1 if employee e works on day d
        works = {}
        for e in range(num_employees):
            for d in range(num_days):
                works[e, d] = model.NewBoolVar(f'works_{e}_{d}')
        
        # is_on_shift[e, s] = 1 if employee e is assigned to shift s
        is_on_shift = {}
        for e in range(num_employees):
            for s in range(num_shifts):
                is_on_shift[e, s] = model.NewBoolVar(f'on_shift_{e}_{s}')
                # Link to shift_assignment
                model.Add(shift_assignment[e] == s).OnlyEnforceIf(is_on_shift[e, s])
                model.Add(shift_assignment[e] != s).OnlyEnforceIf(is_on_shift[e, s].Not())
        
        # Each employee is on exactly one shift
        for e in range(num_employees):
            model.AddExactlyOne([is_on_shift[e, s] for s in range(num_shifts)])
        
        # Constraint: Leave days - employee cannot work on leave days
        for e, emp in enumerate(self.employees):
            for d, dt in enumerate(self.dates):
                if dt in self.leaves[emp.name]:
                    model.Add(works[e, d] == 0)
        
        # Constraint: Minimum staffing per shift per day
        for d, dt in enumerate(self.dates):
            required = self._get_required_staff(dt)
            
            for s in range(num_shifts):
                # Count employees working on this shift on this day
                shift_workers = []
                for e in range(num_employees):
                    # works_on_shift[e, d, s] = is_on_shift[e, s] AND works[e, d]
                    works_on_shift = model.NewBoolVar(f'works_shift_{e}_{d}_{s}')
                    model.AddBoolAnd([is_on_shift[e, s], works[e, d]]).OnlyEnforceIf(works_on_shift)
                    model.AddBoolOr([is_on_shift[e, s].Not(), works[e, d].Not()]).OnlyEnforceIf(works_on_shift.Not())
                    shift_workers.append(works_on_shift)
                
                # At least 'required' people on each shift each day
                model.Add(sum(shift_workers) >= required)
        
        # Constraint: 2 consecutive days off per week
        # Group days into weeks and ensure 2 consecutive offs
        for e in range(num_employees):
            week_start = 0
            while week_start < num_days:
                week_end = min(week_start + 7, num_days)
                week_length = week_end - week_start
                
                if week_length >= 2:
                    # For each week, ensure at least one pair of consecutive days off
                    consecutive_off_options = []
                    for d in range(week_start, week_end - 1):
                        # both_off = works[e, d] == 0 AND works[e, d+1] == 0
                        both_off = model.NewBoolVar(f'consec_off_{e}_{d}')
                        model.AddBoolAnd([works[e, d].Not(), works[e, d + 1].Not()]).OnlyEnforceIf(both_off)
                        model.AddBoolOr([works[e, d], works[e, d + 1]]).OnlyEnforceIf(both_off.Not())
                        consecutive_off_options.append(both_off)
                    
                    if consecutive_off_options:
                        model.AddBoolOr(consecutive_off_options)
                
                week_start += 7
        
        # Constraint: Maximum 6 consecutive working days
        for e in range(num_employees):
            for d in range(num_days - 6):
                # Not all 7 consecutive days can be working
                model.Add(sum(works[e, d + i] for i in range(7)) <= 6)
        
        # Objective: Maximize fairness in work distribution
        # Minimize variance in working days, weekend shifts, night shifts
        
        # Count weekend days worked per employee
        weekend_days_worked = {}
        for e in range(num_employees):
            weekend_work_list = []
            for d, dt in enumerate(self.dates):
                if self._is_weekend(dt):
                    weekend_work_list.append(works[e, d])
            weekend_days_worked[e] = sum(weekend_work_list) if weekend_work_list else 0
        
        # Count total days worked per employee
        total_days_worked = {}
        for e in range(num_employees):
            total_days_worked[e] = sum(works[e, d] for d in range(num_days))
        
        # Fairness: minimize difference between max and min weekend work
        max_weekend = model.NewIntVar(0, num_days, 'max_weekend')
        min_weekend = model.NewIntVar(0, num_days, 'min_weekend')
        
        for e in range(num_employees):
            if isinstance(weekend_days_worked[e], int):
                model.Add(max_weekend >= weekend_days_worked[e])
                model.Add(min_weekend <= weekend_days_worked[e])
            else:
                model.Add(max_weekend >= weekend_days_worked[e])
                model.Add(min_weekend <= weekend_days_worked[e])
        
        weekend_diff = model.NewIntVar(0, num_days, 'weekend_diff')
        model.Add(weekend_diff == max_weekend - min_weekend)
        
        # Fairness: minimize difference between max and min total work
        max_total = model.NewIntVar(0, num_days, 'max_total')
        min_total = model.NewIntVar(0, num_days, 'min_total')
        
        for e in range(num_employees):
            model.Add(max_total >= total_days_worked[e])
            model.Add(min_total <= total_days_worked[e])
        
        total_diff = model.NewIntVar(0, num_days, 'total_diff')
        model.Add(total_diff == max_total - min_total)
        
        # Minimize the sum of differences (weighted)
        model.Minimize(weekend_diff * 10 + total_diff * 5)
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60.0
        status = solver.Solve(model)
        
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            print(f"Could not find a solution. Status: {solver.StatusName(status)}")
            return None
        
        # Extract solution
        roster = Roster(
            month=self.month,
            year=self.year,
            employees=self.employees
        )
        
        # Assign shifts to employees based on solution
        for e, emp in enumerate(self.employees):
            shift_idx = solver.Value(shift_assignment[e])
            emp.assigned_shift = self.shifts[shift_idx]
            
            # Collect days off
            emp.days_off = [
                self.dates[d] for d in range(num_days)
                if solver.Value(works[e, d]) == 0
            ]
        
        # Build schedule
        for d, dt in enumerate(self.dates):
            day_assignment = DayAssignment(
                date=dt,
                day_name=self._get_day_name(dt),
                is_weekend=self._is_weekend(dt)
            )
            
            # Assign employees to each shift
            for s, shift_type in enumerate(self.shifts):
                # Get employees on this shift who are working this day
                shift_employees = []
                for e, emp in enumerate(self.employees):
                    if (solver.Value(is_on_shift[e, s]) == 1 and 
                        solver.Value(works[e, d]) == 1):
                        shift_employees.append(emp)
                
                # Sort by seniority
                shift_employees.sort(key=lambda x: x.seniority_rank)
                
                shift_assignment_obj = day_assignment.get_shift(shift_type)
                
                if len(shift_employees) >= 1:
                    shift_assignment_obj.lead = shift_employees[0]
                if len(shift_employees) >= 2:
                    shift_assignment_obj.backup = shift_employees[1]
                if len(shift_employees) > 2:
                    shift_assignment_obj.members = shift_employees[2:]
            
            roster.schedule.append(day_assignment)
        
        # Calculate statistics
        roster.calculate_statistics()
        
        return roster
    
    def generate_weekly_schedule(self) -> Optional[Roster]:
        """Generate a fixed weekly schedule that repeats all month.
        
        Each employee gets 2 consecutive days off per week.
        Pattern is fixed and repeats every week.
        """
        roster = Roster(
            month=self.month,
            year=self.year,
            employees=self.employees
        )
        
        # Distribute employees round-robin across shifts for fair seniority mix
        shift_groups = {
            ShiftType.SHIFT_1: [],
            ShiftType.SHIFT_2: [],
            ShiftType.SHIFT_3: []
        }
        
        shifts = [ShiftType.SHIFT_1, ShiftType.SHIFT_2, ShiftType.SHIFT_3]
        for i, emp in enumerate(self.employees):
            shift_groups[shifts[i % 3]].append(emp)
        
        # Assign shifts to employees and create fixed weekly patterns
        # 
        # STAFFING REQUIREMENTS per shift:
        #   Mon: 4 staff → 2 people off
        #   Tue: 5 staff → 1 person off
        #   Wed: 5 staff → 1 person off
        #   Thu: 5 staff → 1 person off
        #   Fri: 4 staff → 2 people off
        #   Sat: 4 staff → 2 people off
        #   Sun: 3 staff → 3 people off
        #
        # Off patterns calculated to meet exact requirements:
        # (Day indices: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)
        off_patterns = [
            [1, 2],  # Tue-Wed off (1 person)
            [3, 4],  # Thu-Fri off (1 person)
            [4, 5],  # Fri-Sat off (1 person)
            [5, 6],  # Sat-Sun off (1 person)
            [6, 0],  # Sun-Mon off (1st person)
            [6, 0],  # Sun-Mon off (2nd person)
        ]
        
        import random
        
        for shift_type, group in shift_groups.items():
            # Shuffle the patterns so different people get different offs each month
            # (but still maintains correct staffing counts)
            shuffled_patterns = off_patterns.copy()
            random.shuffle(shuffled_patterns)
            
            for idx, emp in enumerate(group):
                emp.assigned_shift = shift_type
                
                # Assign off days from shuffled patterns
                pattern_idx = idx % len(shuffled_patterns)
                off_days = shuffled_patterns[pattern_idx]
                
                # Create weekly pattern: True = working, False = off
                emp.weekly_pattern = {}
                for day in range(7):  # 0=Mon, 6=Sun
                    emp.weekly_pattern[day] = day not in off_days
        
        # Generate schedule for all days in month
        for d, dt in enumerate(self.dates):
            day_idx = dt.weekday()  # 0=Mon, 6=Sun
            
            day_assignment = DayAssignment(
                date=dt,
                day_name=self._get_day_name(dt),
                is_weekend=self._is_weekend(dt)
            )
            
            for shift_type, group in shift_groups.items():
                # Get employees working today based on weekly pattern
                working_today = []
                for emp in group:
                    # Check leave first
                    if dt in self.leaves[emp.name]:
                        continue
                    # Check weekly pattern
                    if emp.weekly_pattern.get(day_idx, True):
                        working_today.append(emp)
                
                # Sort by seniority
                working_today.sort(key=lambda e: e.seniority_rank)
                
                shift_assignment = day_assignment.get_shift(shift_type)
                
                if len(working_today) >= 1:
                    shift_assignment.lead = working_today[0]
                if len(working_today) >= 2:
                    shift_assignment.backup = working_today[1]
                if len(working_today) > 2:
                    shift_assignment.members = working_today[2:]
            
            roster.schedule.append(day_assignment)
        
        roster.calculate_statistics()
        return roster
    
    def generate_fallback(self) -> Optional[Roster]:
        """Alias for generate_weekly_schedule for backward compatibility."""
        return self.generate_weekly_schedule()
