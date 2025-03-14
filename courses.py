from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, Course, Category, User, Review
from tools import CoursesFilter, ImageSaver
from sqlalchemy import func

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]

REVIEW_PARAMS = ['rating', 'text']

def params():
    return {p: request.form.get(p) or None for p in COURSE_PARAMS}

def review_params():
    return {p: request.form.get(p) or None for p in REVIEW_PARAMS}

def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }

@bp.route('/')
def index():
    courses = CoursesFilter(**search_params()).perform()
    pagination = db.paginate(courses)
    courses = pagination.items
    categories = db.session.execute(db.select(Category)).scalars()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())

@bp.route('/new')
@login_required
def new():
    course = Course()
    categories = db.session.execute(db.select(Category)).scalars()
    users = db.session.execute(db.select(User)).scalars()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users,
                           course=course)

@bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.files.get('background_img')
    img = None
    course = Course()
    try:
        if f and f.filename:
            img = ImageSaver(f).save()

        image_id = img.id if img else None
        course = Course(**params(), background_image_id=image_id)
        db.session.add(course)
        db.session.commit()
    except IntegrityError as err:
        flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
        db.session.rollback()
        categories = db.session.execute(db.select(Category)).scalars()
        users = db.session.execute(db.select(User)).scalars()
        return render_template('courses/new.html',
                            categories=categories,
                            users=users,
                            course=course)

    flash(f'Курс {course.name} был успешно добавлен!', 'success')

    return redirect(url_for('courses.index'))

@bp.route('/<int:course_id>', methods=['GET', 'POST'])
def show(course_id):
    course = db.get_or_404(Course, course_id)
    reviews = db.session.execute(db.select(Review).filter_by(course_id=course_id).order_by(Review.created_at.desc()).limit(5)).scalars()

    user_review = None
    if current_user.is_authenticated:
        user_review = db.session.execute(db.select(Review).filter_by(course_id=course_id, user_id=current_user.id)).scalar()

    if request.method == 'POST' and current_user.is_authenticated:
        try:
            if not user_review: # only create a new review if one doesnt exist
                review = Review(course_id=course_id, user_id=current_user.id, **review_params())
                db.session.add(review)

                course.rating_sum += int(review.rating)
                course.rating_num += 1
                db.session.commit()
            else:
                flash('Вы уже оставили отзыв к этому курсу.', 'warning')

        except IntegrityError as err:
            flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
            db.session.rollback()

        return redirect(url_for('courses.show', course_id=course_id))

    return render_template('courses/show.html', course=course, reviews=list(reviews), user_review=user_review)

@bp.route('/<int:course_id>/reviews', methods=['GET', 'POST'])
def reviews(course_id):
    course = db.get_or_404(Course, course_id)

    sort_by = request.args.get('sort_by', 'newest')
    query = db.select(Review).filter_by(course_id=course_id)

    if sort_by == 'positive':
        query = query.order_by(Review.rating.desc(), Review.created_at.desc())
    elif sort_by == 'negative':
        query = query.order_by(Review.rating.asc(), Review.created_at.desc())
    else: # newest
        query = query.order_by(Review.created_at.desc())

    pagination = db.paginate(query, per_page=5)
    reviews = pagination.items

    user_review = None
    if current_user.is_authenticated:
        user_review = db.session.execute(db.select(Review).filter_by(course_id=course_id, user_id=current_user.id)).scalar()

    if request.method == 'POST' and current_user.is_authenticated:
        try:
            if not user_review: # only create a new review if one doesnt exist
                review = Review(course_id=course_id, user_id=current_user.id, **review_params())
                db.session.add(review)

                course.rating_sum += int(review.rating)
                course.rating_num += 1
                db.session.commit()
            else:
                flash('Вы уже оставили отзыв к этому курсу.', 'warning')

        except IntegrityError as err:
            flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
            db.session.rollback()

        return redirect(url_for('courses.reviews', course_id=course_id, sort_by=sort_by))

    return render_template('courses/reviews.html', course=course, reviews=reviews, pagination=pagination, sort_by=sort_by, user_review=user_review)
