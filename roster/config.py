"""
Configuration management for EOC Roster Generator.
Handles loading/saving team configurations and roster history.
"""

import json
import os
from datetime import datetime, date
from typing import List, Optional, Dict
from pathlib import Path

from roster.models import Employee


class ConfigManager:
    """Manages team configuration and roster history persistence."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize config manager with data directory path."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.team_config_path = self.data_dir / "team_config.json"
        self.roster_history_path = self.data_dir / "roster_history.json"
    
    def save_team_config(self, employees: List[Employee]) -> bool:
        """Save team configuration to JSON file."""
        try:
            config = {
                "team": [emp.to_dict() for emp in employees],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.team_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving team config: {e}")
            return False
    
    def load_team_config(self) -> Optional[List[Employee]]:
        """Load team configuration from JSON file."""
        if not self.team_config_path.exists():
            return None
        
        try:
            with open(self.team_config_path, 'r') as f:
                config = json.load(f)
            
            employees = [Employee.from_dict(emp_data) for emp_data in config.get("team", [])]
            return employees if employees else None
        
        except Exception as e:
            print(f"Error loading team config: {e}")
            return None
    
    def has_team_config(self) -> bool:
        """Check if team configuration file exists."""
        return self.team_config_path.exists()
    
    def get_last_updated(self) -> Optional[str]:
        """Get the last updated timestamp of team config."""
        if not self.team_config_path.exists():
            return None
        
        try:
            with open(self.team_config_path, 'r') as f:
                config = json.load(f)
            return config.get("last_updated")
        except:
            return None
    
    def save_roster_history(self, month: int, year: int, employee_stats: Dict[str, dict]) -> bool:
        """Save roster history for fairness tracking across months."""
        try:
            history = self.load_roster_history() or {}
            
            key = f"{year}-{month:02d}"
            history[key] = {
                "generated_at": datetime.now().isoformat(),
                "employees": employee_stats
            }
            
            with open(self.roster_history_path, 'w') as f:
                json.dump(history, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving roster history: {e}")
            return False
    
    def load_roster_history(self) -> Optional[Dict]:
        """Load complete roster history."""
        if not self.roster_history_path.exists():
            return None
        
        try:
            with open(self.roster_history_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading roster history: {e}")
            return None
    
    def get_previous_month_stats(self, current_month: int, current_year: int) -> Optional[Dict]:
        """Get statistics from the previous month for fairness balancing."""
        history = self.load_roster_history()
        if not history:
            return None
        
        # Calculate previous month
        if current_month == 1:
            prev_month, prev_year = 12, current_year - 1
        else:
            prev_month, prev_year = current_month - 1, current_year
        
        key = f"{prev_year}-{prev_month:02d}"
        return history.get(key, {}).get("employees")
    
    def get_sample_team(self) -> List[Employee]:
        """Return a sample team of 18 members for testing."""
        sample_names = [
            "John Anderson", "Sarah Mitchell", "Michael Chen", "Emily Rodriguez",
            "David Kim", "Jessica Taylor", "Robert Wilson", "Amanda Martinez",
            "Christopher Lee", "Jennifer Garcia", "Matthew Brown", "Ashley Johnson",
            "Daniel Thompson", "Stephanie White", "Andrew Davis", "Nicole Miller",
            "Joshua Moore", "Rachel Jackson"
        ]
        
        return [
            Employee(name=name, seniority_rank=i+1)
            for i, name in enumerate(sample_names)
        ]
    
    def validate_employees(self, employees: List[Employee]) -> tuple[bool, List[str]]:
        """Validate employee list for errors."""
        errors = []
        
        # Check count
        if len(employees) < 9:
            errors.append(f"Need at least 9 employees for minimum coverage. Got: {len(employees)}")
        
        # Check for duplicate seniority ranks
        ranks = [emp.seniority_rank for emp in employees]
        if len(ranks) != len(set(ranks)):
            duplicates = [r for r in ranks if ranks.count(r) > 1]
            errors.append(f"Duplicate seniority ranks found: {set(duplicates)}")
        
        # Check for duplicate names
        names = [emp.name for emp in employees]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            errors.append(f"Duplicate names found: {set(duplicates)}")
        
        # Check seniority range
        for emp in employees:
            if emp.seniority_rank < 1 or emp.seniority_rank > len(employees):
                errors.append(f"Invalid seniority rank for {emp.name}: {emp.seniority_rank}")
        
        return (len(errors) == 0, errors)
