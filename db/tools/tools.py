from datetime import date
from typing import Optional
from db.models import SemesterSettings

def get_week_type_for_date(target_date: date, semester: SemesterSettings) -> Optional[str]:
    """Определение типа недели по дате"""
    if not semester or target_date < semester.start_date or target_date > semester.end_date:
        return None
    weeks_passed = (target_date - semester.start_date).days // 7
    if semester.first_week_type == 'upper':
        return 'upper' if weeks_passed % 2 == 0 else 'lower'
    return 'lower' if weeks_passed % 2 == 0 else 'upper'