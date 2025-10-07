from datetime import datetime, date, time
from typing import Optional
from sqlalchemy import (Column, Integer, String, Boolean, DateTime, Date, Time, Text, ForeignKey, BigInteger,
                        CheckConstraint, UniqueConstraint, func)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker

Base = declarative_base()


class Group(Base):
    """Студенческая группа"""
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    faculty_id: Mapped[Optional[int]] = mapped_column(ForeignKey('faculties.id'), nullable=False)
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    student_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    schedules = relationship("Schedule", back_populates="group", cascade="all, delete-orphan")
    users = relationship("BotUser", back_populates="group")
    faculty = relationship("Faculty", back_populates='groups')

    def __repr__(self):
        return f"Группа {self.name}"


class Faculty(Base):
    """Факультет"""
    __tablename__ = 'faculties'
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(Text)

    groups = relationship('Group', back_populates='faculty')


class TeacherSubject(Base):
    """Предмет -> преподаватель"""
    __tablename__ = 'teacher_subject'

    teacher_id: Mapped[int] = mapped_column(ForeignKey('teachers.id'), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey('subjects.id'), primary_key=True)

    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    qualification: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    teacher = relationship('Teacher', back_populates='teacher_subjects')
    subject = relationship("Subject", back_populates='teacher_subjects')


class Teacher(Base):
    """Преподаватели"""
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    middle_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    schedules = relationship("Schedule", back_populates="teacher")
    schedule_changes = relationship("ScheduleChange", foreign_keys="ScheduleChange.new_teacher_id")

    teacher_subjects = relationship("TeacherSubject", back_populates='teacher')
    subjects = relationship("Subject", secondary='teacher_subject', viewonly=True)

    def __repr__(self):
        return f'Преподаватель {self.last_name} {self.first_name[0]}. {self.middle_name[0]}.'


class Room(Base):
    """Аудитории"""
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    schedules = relationship("Schedule", back_populates="room")
    schedule_changes = relationship("ScheduleChange", foreign_keys="ScheduleChange.new_room_id")

    def __repr__(self):
        return f'Аудитория {self.number}'


class Subject(Base):
    """Предмет"""
    __tablename__ = 'subjects'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    schedules = relationship("Schedule", back_populates="subject")
    schedule_changes = relationship("ScheduleChange", foreign_keys="ScheduleChange.new_subject_id")

    teacher_subjects = relationship("TeacherSubject", back_populates='subject')
    teachers = relationship('Teacher', secondary='teacher_subject', viewonly=True)

    def __repr__(self):
        return f'Предмет {self.name}'


class LessonType(Base):
    """Тип занятия(лекция, практика, лабораторная)"""
    __tablename__ = "lesson_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    short_name: Mapped[str] = mapped_column(String(20), nullable=False)

    schedules = relationship("Schedule", back_populates="lesson_type")

    def __repr__(self):
        return f"Тип занятия {self.name}"


class TimeSlot(Base):
    """Время пары"""
    __tablename__ = "time_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    slot_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    schedules = relationship("Schedule", back_populates="time_slot")
    schedule_changes = relationship("ScheduleChange", foreign_keys="ScheduleChange.new_time_slot_id")

    def __repr__(self):
        return f"Время пары {self.slot_number}: {self.start_time} - {self.end_time}"


class Schedule(Base):
    """Расписание"""
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(primary_key=True)

    group_id: Mapped[int] = mapped_column(ForeignKey('groups.id', ondelete='CASCADE'), nullable=False)
    subject_id: Mapped[Optional[int]] = mapped_column(ForeignKey('subjects.id'))
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey('teachers.id'))
    room_id: Mapped[Optional[int]] = mapped_column(ForeignKey('rooms.id'))
    lesson_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey('lesson_types.id'))
    time_slot_id: Mapped[int] = mapped_column(ForeignKey('time_slots.id'), nullable=False)

    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    week_type: Mapped[str] = mapped_column(String(10), nullable=False)

    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint('day_of_week >= 1 AND day_of_week <= 6', name='check_day_of_week'),
        CheckConstraint("week_type IN ('upper', 'lower', 'both')", name='check_week_type'),
        UniqueConstraint('group_id', 'day_of_week', 'time_slot_id', 'week_type', name='unique_schedule_slot')
    )

    group = relationship("Group", back_populates="schedules")
    subject = relationship("Subject", back_populates="schedules")
    teacher = relationship("Teacher", back_populates="schedules")
    room = relationship("Room", back_populates="schedules")
    lesson_type = relationship("LessonType", back_populates="schedules")
    time_slot = relationship("TimeSlot", back_populates="schedules")
    changes = relationship("ScheduleChange", back_populates="original_schedule", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Расписание {self.group.name}, {self.day_of_week}, {self.time_slot.slot_number}"


class BotUser(Base):
    """ТГ пользователь"""
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100))
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))

    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey('groups.id'))

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notifications_time: Mapped[time] = mapped_column(Time, default=time(19, 0))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    group = relationship("Group", back_populates="users")
    created_changes = relationship("ScheduleChange", back_populates='created_by_user')

    def __repr__(self):
        return f'Пользователь {self.first_name} {self.user_id}'


class SemesterSettings(Base):
    """Настройки семестра"""
    __tablename__ = "semester_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    first_week_type: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    __table_args__ = (
        CheckConstraint("first_week_type IN ('upper', 'lower', 'both')", name="check_first_week_type"),
    )

    def __repr__(self):
        return f"Семестр {self.semester_name}"


class ScheduleChange(Base):
    """Замена, изменение занятия"""
    __tablename__ = "schedule_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_schedule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('schedule.id', ondelete="CASCADE")
    )
    change_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    new_subject_id: Mapped[Optional[int]] = mapped_column(ForeignKey('subjects.id'))
    new_teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey('teachers.id'))
    new_room_id: Mapped[Optional[int]] = mapped_column(ForeignKey('rooms.id'))
    new_time_slot_id: Mapped[Optional[int]] = mapped_column(ForeignKey('time_slots.id'))

    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(Text)

    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey('bot_users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    original_schedule = relationship("Schedule", back_populates="changes")
    new_subject = relationship("Subject")
    new_teacher = relationship("Teacher")
    new_room = relationship("Room")
    new_time_slot = relationship("TimeSlot")
    created_by_user = relationship("BotUser", back_populates='created_changes')

    def __repr__(self):
        return f'Изменение в расписании {self.change_date} {self.id}'


class AdminUser(Base):
    """Администратор веб-панели"""
    __tablename__ = 'admin_users'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(50), default='editor')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self):
        return f'Админ {self.username} {self.role}'
