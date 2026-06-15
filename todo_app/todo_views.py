from flask import (
    Blueprint, render_template, request, redirect, url_for, g, abort
)

from .auth_views import login_required
from .models import Todo
from . import db

bp = Blueprint('todo_views', __name__, url_prefix='/todo')

@bp.route('/list')
@login_required # decorator: authentication middleware
def index():
    todos = Todo.query.order_by(Todo.id.desc()).filter(Todo.created_by == g.user.id).all()

    return render_template('todo/index.html', todos = todos)

@bp.route('/create', methods = ('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        todo = Todo(g.user.id, title, description)
        db.session.add(todo)
        db.session.commit()

        return redirect(url_for('todo_views.index'))

    return render_template('todo/create.html')

def get_todo_by_id(id):
    # Scope to the owner so a logged-in user cannot read/mutate
    # another user's todo by guessing its id (IDOR).
    todo = Todo.query.filter_by(id=id, created_by=g.user.id).first()
    if todo is None:
        abort(404)

    return todo

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    todo = get_todo_by_id(id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()

        # Validate before saving; on failure re-render the edit row with the
        # message inline and the user's input preserved. Returned with a 200 so
        # HTMX swaps it in (HTMX only swaps 2xx/3xx responses by default).
        if not (3 <= len(title) <= 100):
            return render_template(
                'todo/todo_row_edit.partial.html',
                todo=todo,
                title=title,
                description=description,
                error='Title must be between 3 and 100 characters.',
            )

        todo.title = title
        todo.description = description
        db.session.commit()

        return render_template('todo/todo_row.partial.html', todo=todo)

    return render_template(
        'todo/todo_row_edit.partial.html',
        todo=todo,
        title=todo.title,
        description=todo.description,
        error=None,
    )

@bp.route('/row/<int:id>')
@login_required
def row(id):
    # Display row on its own — used as the "Cancel" target to swap an editing
    # row back to its read-only form.
    return render_template('todo/todo_row.partial.html', todo=get_todo_by_id(id))

@bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle(id):
    todo = get_todo_by_id(id)
    todo.status = not todo.status
    db.session.commit()

    return render_template('todo/todo_row.partial.html', todo=todo)

@bp.route('/delete/<int:id>', methods=["DELETE"])
@login_required
def delete(id):
    db.session.delete(get_todo_by_id(id))
    db.session.commit()

    return ''
