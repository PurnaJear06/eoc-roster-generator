"""
Terminal CLI interface for EOC Roster Generator.
Beautiful interactive prompts using the Rich library.
"""

import sys
import os
from datetime import date, datetime
from typing import List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich import box
import pyfiglet

from roster.models import Employee, Roster, ShiftType
from roster.config import ConfigManager
from roster.scheduler import RosterScheduler
from roster.exporter import RosterExporter


class RosterCLI:
    """Interactive terminal interface for roster generation."""
    
    # ASCII art header
    HEADER = """
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║     ███████╗ ██████╗  ██████╗                                  ║
║     ██╔════╝██╔═══██╗██╔════╝                                  ║
║     █████╗  ██║   ██║██║                                       ║
║     ██╔══╝  ██║   ██║██║                                       ║
║     ███████╗╚██████╔╝╚██████╗                                  ║
║     ╚══════╝ ╚═════╝  ╚═════╝                                  ║
║                                                                ║
║           ROSTER AUTOMATION SYSTEM v1.0                        ║
║                                                                ║
║   "Great teams aren't built on talent alone,                   ║
║    but on smart scheduling and fair rotations."                ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"""
    
    def __init__(self):
        """Initialize CLI with Rich console."""
        self.console = Console()
        self.config = ConfigManager()
        self.exporter = RosterExporter()
        self.employees: List[Employee] = []
        self.current_roster: Optional[Roster] = None
        self.current_month: int = 0
        self.current_year: int = 0
    
    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self):
        """Display the ASCII art header."""
        self.console.print(self.HEADER, style="bold cyan")
    
    def display_welcome(self):
        """Display welcome message and menu."""
        self.clear_screen()
        self.display_header()
        self.console.print()
    
    def main_menu(self) -> str:
        """Display main menu and get user choice."""
        self.console.print("\n[bold]What would you like to do?[/bold]\n")
        
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        table.add_column("Option", style="bold cyan")
        table.add_column("Description")
        
        table.add_row("1", "Generate NEW roster for a month")
        table.add_row("2", "Manage Team Configuration")
        table.add_row("3", "Load existing team configuration")
        table.add_row("4", "Exit")
        
        self.console.print(table)
        self.console.print()
        
        choice = Prompt.ask(
            "[bold]Choice[/bold]",
            choices=["1", "2", "3", "4"],
            default="1"
        )
        
        return choice
    
    def get_month_year(self) -> Tuple[int, int]:
        """Get month and year from user."""
        self.console.print("\n[bold]═══ MONTH SELECTION ═══[/bold]\n")
        
        current_year = datetime.now().year
        
        month = IntPrompt.ask(
            "Enter month (1-12)",
            default=datetime.now().month
        )
        while month < 1 or month > 12:
            self.console.print("[red]Invalid month. Please enter 1-12.[/red]")
            month = IntPrompt.ask("Enter month (1-12)")
        
        year = IntPrompt.ask(
            "Enter year",
            default=current_year
        )
        while year < current_year - 1 or year > current_year + 2:
            self.console.print(f"[red]Please enter a year between {current_year-1} and {current_year+2}.[/red]")
            year = IntPrompt.ask("Enter year")
        
        import calendar
        month_name = calendar.month_name[month]
        days = calendar.monthrange(year, month)[1]
        
        self.console.print(f"\n[green]✓[/green] Generating roster for: [bold]{month_name} {year}[/bold] ({days} days)")
        
        return month, year
    
    def setup_team(self) -> List[Employee]:
        """Interactive team setup wizard."""
        self.console.print("\n[bold]═══ TEAM CONFIGURATION ═══[/bold]\n")
        
        # Check if existing config exists
        if self.config.has_team_config():
            last_updated = self.config.get_last_updated()
            self.console.print(f"[yellow]Existing configuration found (last updated: {last_updated})[/yellow]")
            
            if Confirm.ask("Load existing configuration?", default=True):
                employees = self.config.load_team_config()
                if employees:
                    self.console.print(f"[green]✓[/green] Loaded {len(employees)} team members")
                    self._display_team_table(employees)
                    return employees
        
        # Use sample team or create new
        use_sample = Confirm.ask(
            "Would you like to use a sample team of 18 members for testing?",
            default=True
        )
        
        if use_sample:
            employees = self.config.get_sample_team()
            self.console.print(f"[green]✓[/green] Using sample team of {len(employees)} members")
            self._display_team_table(employees)
        else:
            employees = self._manual_team_entry()
        
        # Save configuration
        if Confirm.ask("\nSave this configuration for future use?", default=True):
            if self.config.save_team_config(employees):
                self.console.print("[green]✓[/green] Team configuration saved!")
            else:
                self.console.print("[red]✗[/red] Failed to save configuration")
        
        return employees
    
    def _manual_team_entry(self) -> List[Employee]:
        """Manually enter team members."""
        self.console.print("\n[bold]Enter details for each team member:[/bold]\n")
        
        num_members = IntPrompt.ask(
            "Total team members",
            default=18
        )
        
        employees = []
        used_ranks = set()
        
        for i in range(num_members):
            self.console.print(f"\n[cyan]Member #{i+1}:[/cyan]")
            
            name = Prompt.ask("  Name")
            
            # Get unique seniority rank
            while True:
                rank = IntPrompt.ask(
                    f"  Seniority Rank (1-{num_members}, 1=highest)",
                )
                if rank in used_ranks:
                    self.console.print(f"[red]Rank {rank} already assigned. Choose another.[/red]")
                elif rank < 1 or rank > num_members:
                    self.console.print(f"[red]Rank must be between 1 and {num_members}.[/red]")
                else:
                    used_ranks.add(rank)
                    break
            
            employees.append(Employee(name=name, seniority_rank=rank))
        
        self.console.print(f"\n[green]✓[/green] {len(employees)} team members configured!")
        return employees
    
    def _display_team_table(self, employees: List[Employee]):
        """Display team members in a table."""
        table = Table(title="Team Roster", box=box.ROUNDED)
        table.add_column("Rank", style="cyan", justify="center")
        table.add_column("Name", style="white")
        
        for emp in sorted(employees, key=lambda e: e.seniority_rank):
            table.add_row(str(emp.seniority_rank), emp.name)
        
        self.console.print(table)
    
    def manage_leaves(self, employees: List[Employee], month: int, year: int) -> List[Employee]:
        """Manage employee leaves for the month."""
        self.console.print("\n[bold]═══ LEAVE & UNAVAILABILITY ═══[/bold]\n")
        
        has_leaves = Confirm.ask(
            "Does anyone have pre-approved leave this month?",
            default=False
        )
        
        if not has_leaves:
            self.console.print("[green]✓[/green] No leaves recorded")
            return employees
        
        num_leaves = IntPrompt.ask("How many people have leaves?", default=1)
        
        import calendar
        max_day = calendar.monthrange(year, month)[1]
        
        for i in range(num_leaves):
            self.console.print(f"\n[cyan]Person #{i+1}:[/cyan]")
            
            # Show available employees
            self.console.print("  Available employees:")
            for emp in employees:
                self.console.print(f"    - {emp.name}")
            
            name = Prompt.ask("  Employee name")
            
            # Find employee
            employee = None
            for emp in employees:
                if emp.name.lower() == name.lower() or name.lower() in emp.name.lower():
                    employee = emp
                    break
            
            if not employee:
                self.console.print(f"[red]Employee '{name}' not found. Skipping.[/red]")
                continue
            
            # Get leave dates
            start_day = IntPrompt.ask(f"  Leave start date (1-{max_day})")
            end_day = IntPrompt.ask(f"  Leave end date (1-{max_day})", default=start_day)
            
            # Validate dates
            if start_day < 1 or end_day > max_day or start_day > end_day:
                self.console.print("[red]Invalid date range. Skipping.[/red]")
                continue
            
            # Record leaves
            for day in range(start_day, end_day + 1):
                leave_date = date(year, month, day)
                if leave_date not in employee.leaves:
                    employee.leaves.append(leave_date)
            
            self.console.print(
                f"[green]✓[/green] Recorded leave for {employee.name}: "
                f"{month}/{start_day} - {month}/{end_day}"
            )
        
        self.console.print("\n[green]✓[/green] Leaves recorded!")
        return employees
    
    def generate_roster(self, employees: List[Employee], month: int, year: int) -> Optional[Roster]:
        """Generate the roster with progress display."""
        self.console.print("\n[bold]═══ GENERATING ROSTER ═══[/bold]\n")
        
        scheduler = RosterScheduler(employees, month, year)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task("Analyzing constraints...", total=None)
            
            # Validate coverage first
            valid, errors = scheduler.validate_coverage()
            if not valid:
                progress.stop()
                self.console.print("\n[red]❌ ERROR: Cannot generate roster[/red]")
                for error in errors:
                    self.console.print(f"   [red]- {error}[/red]")
                return None
            
            progress.update(task, description="Assigning shifts...")
            
            # Generate roster
            progress.update(task, description="Optimizing rotations...")
            roster = scheduler.generate()
            
            if not roster:
                progress.update(task, description="Trying fallback algorithm...")
                roster = scheduler.generate_fallback()
            
            if roster:
                progress.update(task, description="Validating coverage...")
                roster.calculate_statistics()
        
        if roster:
            self._display_summary(roster)
        else:
            self.console.print("\n[red]❌ Failed to generate roster[/red]")
        
        return roster
    
    def _display_summary(self, roster: Roster):
        """Display generation summary."""
        stats = roster.statistics
        
        self.console.print("\n[green]✓[/green] [bold]Roster generated successfully![/bold]\n")
        
        panel_content = f"""
[bold]Summary:[/bold]
├─ Total shifts scheduled: {stats.total_shifts_scheduled}
├─ Weekend shifts per person: avg {stats.avg_weekend_shifts:.1f} (range: {stats.min_weekend_shifts}-{stats.max_weekend_shifts})
├─ Night shifts per person: avg {stats.avg_night_shifts:.1f}
├─ All coverage requirements: [green]MET[/green]
└─ All leaves accommodated: [green]YES[/green]

[bold]Warnings:[/bold] {"None" if not stats.warnings else ", ".join(stats.warnings)}
"""
        
        panel = Panel(
            panel_content,
            title="Generation Complete",
            border_style="green"
        )
        self.console.print(panel)
    
    def export_menu(self, roster: Roster) -> Optional[str]:
        """Display export options and handle export."""
        self.console.print("\n[bold]═══ EXPORT OPTIONS ═══[/bold]\n")
        
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        table.add_column("Option", style="bold cyan")
        table.add_column("Description")
        
        table.add_row("1", "Preview roster summary")
        table.add_row("2", "Export to Excel")
        table.add_row("3", "Export to CSV")
        table.add_row("4", "Both Excel and CSV")
        table.add_row("5", "🔄 Regenerate roster (new shuffle)")
        table.add_row("6", "Cancel")
        
        self.console.print(table)
        
        choice = Prompt.ask(
            "\n[bold]Choice[/bold]",
            choices=["1", "2", "3", "4", "5", "6"],
            default="2"
        )
        
        exported_files = []
        
        if choice == "1":
            self._preview_roster(roster)
            return self.export_menu(roster)  # Show menu again after preview
        
        elif choice == "2":
            filepath = self._export_excel(roster)
            exported_files.append(filepath)
        
        elif choice == "3":
            filepath = self._export_csv(roster)
            exported_files.append(filepath)
        
        elif choice == "4":
            excel_path = self._export_excel(roster)
            csv_path = self._export_csv(roster)
            exported_files.extend([excel_path, csv_path])
        
        elif choice == "5":
            # Regenerate roster with new shuffle
            return self._regenerate_roster()
        
        elif choice == "6":
            self.console.print("[yellow]Export cancelled.[/yellow]")
            return None
        
        if exported_files:
            # Save to history
            if roster.statistics:
                self.config.save_roster_history(
                    roster.month, 
                    roster.year, 
                    roster.statistics.employee_stats
                )
            
            return exported_files[0]
        
        return None
    
    def _preview_roster(self, roster: Roster):
        """Display roster preview in terminal."""
        self.console.print("\n[bold]═══ ROSTER PREVIEW ═══[/bold]\n")
        
        # Show first week
        table = Table(title=f"{roster.get_month_name()} {roster.year} (First 7 days)", box=box.ROUNDED)
        table.add_column("Date", style="cyan")
        table.add_column("Day", style="white")
        table.add_column("Shift 1", style="green")
        table.add_column("Shift 2", style="blue")
        table.add_column("Shift 3", style="magenta")
        
        for day in roster.schedule[:7]:
            s1 = f"{day.shift_1.lead.name.split()[0] if day.shift_1.lead else '-'} (L)"
            s2 = f"{day.shift_2.lead.name.split()[0] if day.shift_2.lead else '-'} (L)"
            s3 = f"{day.shift_3.lead.name.split()[0] if day.shift_3.lead else '-'} (L)"
            
            day_style = "bold" if day.is_weekend else ""
            table.add_row(
                day.date.strftime("%m/%d"),
                day.day_name[:3],
                s1, s2, s3,
                style=day_style
            )
        
        self.console.print(table)
        self.console.print("\n[dim](Showing leads only. Full details in exported file.)[/dim]")
    
    def _export_excel(self, roster: Roster) -> str:
        """Export to Excel with progress."""
        self.console.print("\n📊 Exporting to Excel...")
        filepath = self.exporter.export_to_excel(roster)
        self.console.print(f"[green]✓[/green] File saved: [bold]{filepath}[/bold]")
        return filepath
    
    def _export_csv(self, roster: Roster) -> str:
        """Export to CSV with progress."""
        self.console.print("\n📄 Exporting to CSV...")
        filepath = self.exporter.export_to_csv(roster)
        self.console.print(f"[green]✓[/green] File saved: [bold]{filepath}[/bold]")
        return filepath
    
    def _regenerate_roster(self) -> Optional[str]:
        """Regenerate roster with new shuffle."""
        if not self.employees or not self.current_month or not self.current_year:
            self.console.print("[red]No roster to regenerate. Please generate a roster first.[/red]")
            return None
        
        self.console.print("\n[cyan]🔄 Regenerating roster with new shuffle...[/cyan]")
        
        # Create new scheduler and regenerate
        scheduler = RosterScheduler(self.employees, self.current_month, self.current_year)
        new_roster = scheduler.generate_weekly_schedule()
        
        if new_roster:
            new_roster.calculate_statistics()
            self.current_roster = new_roster
            self._display_summary(new_roster)
            
            # Show export menu again with new roster
            return self.export_menu(new_roster)
        else:
            self.console.print("[red]Failed to regenerate roster.[/red]")
            return None
    
    def team_management_menu(self):
        """Team management sub-menu for editing team configuration."""
        self.console.print("\n[bold]═══ TEAM MANAGEMENT ═══[/bold]\n")
        
        # Load existing team if not loaded
        if not self.employees:
            if self.config.has_team_config():
                self.employees = self.config.load_team_config() or []
            
            if not self.employees:
                self.console.print("[yellow]No team configuration found. Creating new team.[/yellow]")
                self.employees = []
        
        while True:
            self._display_team_table(self.employees) if self.employees else None
            
            self.console.print("\n[bold]Team Management Options:[/bold]\n")
            
            table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
            table.add_column("Option", style="bold cyan")
            table.add_column("Description")
            
            table.add_row("1", "View current team")
            table.add_row("2", "Edit employee name")
            table.add_row("3", "Change seniority rank")
            table.add_row("4", "Add new employee")
            table.add_row("5", "Remove employee")
            table.add_row("6", "💾 Save and exit")
            table.add_row("7", "Cancel without saving")
            
            self.console.print(table)
            
            choice = Prompt.ask(
                "\n[bold]Choice[/bold]",
                choices=["1", "2", "3", "4", "5", "6", "7"],
                default="1"
            )
            
            if choice == "1":
                if self.employees:
                    self._display_team_table(self.employees)
                else:
                    self.console.print("[yellow]No team members yet.[/yellow]")
            
            elif choice == "2":
                self._edit_employee_name()
            
            elif choice == "3":
                self._change_seniority_rank()
            
            elif choice == "4":
                self._add_employee()
            
            elif choice == "5":
                self._remove_employee()
            
            elif choice == "6":
                if self.config.save_team_config(self.employees):
                    self.console.print("[green]✓ Team configuration saved![/green]")
                else:
                    self.console.print("[red]✗ Failed to save configuration[/red]")
                break
            
            elif choice == "7":
                self.console.print("[yellow]Changes discarded.[/yellow]")
                break
    
    def _edit_employee_name(self):
        """Edit an employee's name."""
        if not self.employees:
            self.console.print("[yellow]No employees to edit.[/yellow]")
            return
        
        self._display_team_table(self.employees)
        current_name = Prompt.ask("\nEnter current name to edit")
        
        # Find employee
        employee = None
        for emp in self.employees:
            if emp.name.lower() == current_name.lower() or current_name.lower() in emp.name.lower():
                employee = emp
                break
        
        if not employee:
            self.console.print(f"[red]Employee '{current_name}' not found.[/red]")
            return
        
        new_name = Prompt.ask(f"Enter new name for '{employee.name}'")
        old_name = employee.name
        employee.name = new_name
        self.console.print(f"[green]✓[/green] Renamed '{old_name}' to '{new_name}'")
    
    def _change_seniority_rank(self):
        """Change an employee's seniority rank."""
        if not self.employees:
            self.console.print("[yellow]No employees to modify.[/yellow]")
            return
        
        self._display_team_table(self.employees)
        name = Prompt.ask("\nEnter employee name")
        
        # Find employee
        employee = None
        for emp in self.employees:
            if emp.name.lower() == name.lower() or name.lower() in emp.name.lower():
                employee = emp
                break
        
        if not employee:
            self.console.print(f"[red]Employee '{name}' not found.[/red]")
            return
        
        old_rank = employee.seniority_rank
        new_rank = IntPrompt.ask(
            f"Enter new rank for '{employee.name}' (current: {old_rank})",
            default=old_rank
        )
        
        if new_rank < 1 or new_rank > len(self.employees):
            self.console.print(f"[red]Rank must be between 1 and {len(self.employees)}.[/red]")
            return
        
        # Swap ranks if new rank is taken
        for emp in self.employees:
            if emp.seniority_rank == new_rank and emp != employee:
                emp.seniority_rank = old_rank
                self.console.print(f"[dim]Swapped '{emp.name}' to rank {old_rank}[/dim]")
                break
        
        employee.seniority_rank = new_rank
        self.console.print(f"[green]✓[/green] Changed '{employee.name}' to rank {new_rank}")
    
    def _add_employee(self):
        """Add a new employee to the team."""
        name = Prompt.ask("\nEnter new employee name")
        
        # Check for duplicate names
        for emp in self.employees:
            if emp.name.lower() == name.lower():
                self.console.print(f"[red]Employee '{name}' already exists.[/red]")
                return
        
        new_rank = len(self.employees) + 1
        rank = IntPrompt.ask(
            f"Enter seniority rank (1-{new_rank})",
            default=new_rank
        )
        
        # Shift ranks down if needed
        if rank <= len(self.employees):
            for emp in self.employees:
                if emp.seniority_rank >= rank:
                    emp.seniority_rank += 1
        
        new_employee = Employee(name=name, seniority_rank=rank)
        self.employees.append(new_employee)
        self.employees.sort(key=lambda e: e.seniority_rank)
        
        self.console.print(f"[green]✓[/green] Added '{name}' at rank {rank}")
    
    def _remove_employee(self):
        """Remove an employee from the team."""
        if not self.employees:
            self.console.print("[yellow]No employees to remove.[/yellow]")
            return
        
        self._display_team_table(self.employees)
        name = Prompt.ask("\nEnter employee name to remove")
        
        # Find employee
        employee = None
        for emp in self.employees:
            if emp.name.lower() == name.lower() or name.lower() in emp.name.lower():
                employee = emp
                break
        
        if not employee:
            self.console.print(f"[red]Employee '{name}' not found.[/red]")
            return
        
        if Confirm.ask(f"Remove '{employee.name}' (rank {employee.seniority_rank})?", default=False):
            removed_rank = employee.seniority_rank
            self.employees.remove(employee)
            
            # Shift ranks up
            for emp in self.employees:
                if emp.seniority_rank > removed_rank:
                    emp.seniority_rank -= 1
            
            self.console.print(f"[green]✓[/green] Removed '{employee.name}'")
        else:
            self.console.print("[yellow]Removal cancelled.[/yellow]")

    
    def goodbye(self):
        """Display goodbye message."""
        self.console.print("\n" + "═" * 50)
        self.console.print("\n[bold]Thank you for using EOC Roster Generator![/bold]")
        self.console.print("Goodbye! 👋\n")
    
    def run(self):
        """Main application loop."""
        try:
            self.display_welcome()
            
            while True:
                choice = self.main_menu()
                
                if choice == "4":
                    self.goodbye()
                    break
                
                elif choice == "2":
                    # Manage team configuration
                    self.team_management_menu()
                    continue
                
                elif choice == "3":
                    # Load existing config
                    if self.config.has_team_config():
                        self.employees = self.config.load_team_config() or []
                        if self.employees:
                            self.console.print(f"\n[green]✓[/green] Loaded {len(self.employees)} team members")
                            self._display_team_table(self.employees)
                        else:
                            self.console.print("[red]No saved configuration found.[/red]")
                    else:
                        self.console.print("[yellow]No saved configuration found.[/yellow]")
                    continue
                
                elif choice == "1":
                    # Generate new roster
                    month, year = self.get_month_year()
                    self.current_month = month
                    self.current_year = year
                    
                    # Team setup
                    self.employees = self.setup_team()
                    
                    # Validate team
                    valid, errors = self.config.validate_employees(self.employees)
                    if not valid:
                        self.console.print("\n[red]Team validation failed:[/red]")
                        for error in errors:
                            self.console.print(f"  [red]- {error}[/red]")
                        continue
                    
                    # Leave management
                    self.employees = self.manage_leaves(self.employees, month, year)
                    
                    # Generate roster
                    roster = self.generate_roster(self.employees, month, year)
                    
                    if roster:
                        self.current_roster = roster
                        self.export_menu(roster)
                    
                    # Ask to generate another
                    if not Confirm.ask("\nGenerate another month?", default=False):
                        self.goodbye()
                        break
                    
                    self.display_welcome()
        
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]Interrupted by user.[/yellow]")
            self.goodbye()
