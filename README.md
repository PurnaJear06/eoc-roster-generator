# EOC Roster Generator

A Python-based terminal application that generates optimized monthly shift rosters for an 18-member EOC team working 24/7 operations with 8-hour rotational shifts.

![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)

## Features

- **Smart Scheduling**: Uses OR-Tools constraint satisfaction solver for optimal shift assignments
- **Fair Distribution**: Balances weekend and night shifts across team members
- **Leave Management**: Handles pre-approved leaves without breaking coverage
- **Beautiful Terminal UI**: Rich text formatting with ASCII art header and progress spinners
- **Excel Export**: Professionally formatted spreadsheets with 3 sheets:
  - Monthly Calendar View (color-coded leads/backups)
  - Individual Employee Schedules
  - Statistics & Fairness Analysis
- **Configuration Persistence**: Save and reuse team configurations

## Shift Configuration

| Shift | Time (EST) | Time (IST) |
|-------|------------|------------|
| Shift 1 | 7:00 AM – 3:00 PM | 1:30 PM – 9:30 PM |
| Shift 2 | 3:00 PM – 11:00 PM | 9:30 PM – 5:30 AM |
| Shift 3 | 11:00 PM – 7:00 AM | 5:30 AM – 1:30 PM |

## Staffing Requirements

- **Weekdays (Mon-Fri)**: 4 people per shift (12 total/day)
- **Weekends (Sat-Sun)**: 3 people per shift (9 total/day)

## Installation

1. **Clone the repository** or navigate to the project directory:
   ```bash
   cd eoc-roster-generator
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:

```bash
python eoc_roster_generator.py
```

### Step-by-Step Flow

1. **Main Menu**: Choose to generate a new roster, load existing config, or exit
2. **Month Selection**: Enter the target month and year
3. **Team Setup**: Use sample team (18 members) or enter manually
4. **Leave Management**: Record any pre-approved leaves
5. **Generation**: Watch the optimizer work with progress indicators
6. **Export**: Preview, export to Excel, CSV, or both

### Sample Output

```
╔════════════════════════════════════════════════════════════════╗
║     ███████╗ ██████╗  ██████╗                                  ║
║     ██╔════╝██╔═══██╗██╔════╝                                  ║
║     █████╗  ██║   ██║██║                                       ║
║     ...                                                        ║
║           ROSTER AUTOMATION SYSTEM v1.0                        ║
╚════════════════════════════════════════════════════════════════╝

What would you like to do?

  1  Generate NEW roster for a month
  2  Load existing team configuration
  3  Exit
```

## Constraints Enforced

- ✅ Minimum staffing met every day (4 weekdays, 3 weekends per shift)
- ✅ Each shift has designated Lead + Backup (by seniority)
- ✅ 2 consecutive weekly offs per person per week
- ✅ Monthly shift consistency (no mid-month changes)
- ✅ Maximum 6 consecutive working days
- ✅ Fair distribution of weekend shifts
- ✅ Fair distribution of night shifts
- ✅ Leave dates honored

## File Structure

```
eoc-roster-generator/
├── eoc_roster_generator.py   # Main entry point
├── requirements.txt          # Dependencies
├── README.md                 # This file
├── roster/
│   ├── __init__.py          # Package exports
│   ├── cli.py               # Terminal UI
│   ├── config.py            # Configuration management
│   ├── exporter.py          # Excel/CSV export
│   ├── models.py            # Data classes
│   └── scheduler.py         # Constraint satisfaction algorithm
├── data/                    # Saved configurations
│   ├── team_config.json
│   └── roster_history.json
└── output/                  # Generated roster files
    └── EOC_Roster_*.xlsx
```

## Troubleshooting

### "Cannot generate roster" error
- Check if you have enough team members (minimum 9 for coverage)
- Reduce the number of leaves on any single day
- Ensure no day has more leaves than can be covered

### Solver timeout
- The solver has a 60-second timeout
- For complex constraints, the fallback greedy algorithm will be used

### Dependencies not found
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## License

MIT License - Feel free to use and modify for your team's needs.

---

*"Great teams aren't built on talent alone, but on smart scheduling and fair rotations."*
