import os
from typing import Optional, Union, List
from datetime import datetime
import sqlalchemy as sa
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from flask import url_for, Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, Text, Integer, MetaData


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    })


db = SQLAlchemy(model_class=Base)


class Category(Base):
    __tablename__ = 'categories'

    id = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))

    def __repr__(self):
        return '<Category %r>' % self.name


class User(Base, UserMixin):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    login: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return ' '.join([self.last_name, self.first_name, self.middle_name or ''])

    def __repr__(self):
        return '<User %r>' % self.login


class Course(Base):
    __tablename__ = 'courses'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    short_desc: Mapped[str] = mapped_column(Text)
    full_desc: Mapped[str] = mapped_column(Text)
    rating_sum: Mapped[int] = mapped_column(default=0)
    rating_num: Mapped[int] = mapped_column(default=0)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    background_image_id: Mapped[str] = mapped_column(ForeignKey("images.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    author: Mapped["User"] = relationship()
    category: Mapped["Category"] = relationship(lazy=False)
    bg_image: Mapped["Image"] = relationship()
    reviews: Mapped[List["Review"]] = relationship(back_populates="course")

    def __repr__(self):
        return '<Course %r>' % self.name

    @property
    def rating(self):
        if self.rating_num > 0:
            return self.rating_sum / self.rating_num
        return 0


class Image(db.Model):
    __tablename__ = 'images'

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(100))
    mime_type: Mapped[str] = mapped_column(String(100))
    md5_hash: Mapped[str] = mapped_column(String(100), unique=True)
    object_id: Mapped[Optional[int]]
    object_type: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    def __repr__(self):
        return '<Image %r>' % self.file_name

    @property
    def storage_filename(self):
        _, ext = os.path.splitext(self.file_name)
        return self.id + ext

    @property
    def url(self):
        return url_for('image', image_id=self.id)


class Review(Base):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(primary_key=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    course: Mapped["Course"] = relationship(back_populates="reviews")
    user: Mapped["User"] = relationship()

    def __repr__(self):
        return f'<Review {self.id} for Course {self.course_id} by User {self.user_id}>'


# ***IMPORTANT: Create a Flask application instance***
app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)  # Initialize the db with the app

# Then create all tables
with app.app_context():
    db.create_all()

    # Create a sample user to add reviews for
    автор = db.session.get(User, 1)  # Replace with real user ID if needed
    if not автор:
        print("Автор с ID 1 не найден. Сначала создайте пользователя.")
        exit()

    # Get a course
    курс_1 = db.session.get(Course, 1)  # Replace with real course ID if needed
    курс_2 = db.session.get(Course, 2)  # Replace with real course ID if needed
    if not курс_1 or not курс_2:
        print("Курс не найден. Проверьте ID курса.")
        exit()

    # Create 5 reviews for each course
    for i in range(5):
        db.session.add(Review(
            rating=4,  # Example rating, change as necessary
            text=f"Отличный курс! Рейтинг: {i+1}/5",  # Sample review text
            course_id=курс_1.id,
            user_id=автор.id,
        ))
        db.session.add(Review(
            rating=5,  # Example rating, change as necessary
            text=f"Очень понравился курс! Рейтинг: {i+1}/5",  # Sample review text
            course_id=курс_2.id,
            user_id=автор.id,
        ))

    # Commit the reviews to the database
    db.session.commit()

    print(f"5 отзывов добавлены на курсы {курс_1.name} и {курс_2.name}")
