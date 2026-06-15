from flask import (
    Blueprint, render_template, request, redirect, url_for, g, flash,
    make_response, abort
)

from .auth_views import login_required
from .models import Todo
from . import db

bp = Blueprint('todo_views', __name__, url_prefix='/todo')

def _board_context():
    """Tasks for the current user plus the overview counts shown on the workbench."""
    todos = Todo.query.order_by(Todo.id.desc()).filter(Todo.created_by == g.user.id).all()
    completed = sum(1 for todo in todos if todo.status)
    total = len(todos)
    stats = {'total': total, 'completed': completed, 'pending': total - completed}

    return {'todos': todos, 'stats': stats}

@bp.route('/list')
@login_required # decorator: authentication middleware
def index():
    return render_template('todo/index.html', **_board_context())

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

@bp.route('/quick', methods=['POST'])
@login_required
def quick_create():
    """Title-only inline add used by the workbench quick-add form (HTMX)."""
    title = request.form.get('title', '').strip()
    if len(title) < 3:
        return render_template('todo/add_status.partial.html',
                               error='Title must be at least 3 characters.')
    if len(title) > 100:
        return render_template('todo/add_status.partial.html',
                               error='Title must be 100 characters or fewer.')

    db.session.add(Todo(g.user.id, title, ''))
    db.session.commit()

    # Confirm in the status slot, refresh stats + list out-of-band, and signal the
    # client (via HX-Trigger) that it is safe to reset and refocus the input.
    html = render_template('todo/add_status.partial.html', success=True)
    html += render_template('todo/board.partial.html', oob=True, **_board_context())
    response = make_response(html)
    response.headers['HX-Trigger'] = 'todoAdded'

    return response

@bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle(id):
    """Flip a task's completed state from the workbench, then re-render the board."""
    todo = Todo.query.get_or_404(id)
    if todo.created_by != g.user.id:
        abort(404)

    todo.status = not todo.status
    db.session.commit()

    return render_template('todo/board.partial.html', **_board_context())

def get_todo_by_id(id):
    return Todo.query.get_or_404(id)

@bp.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    todo = get_todo_by_id(id)
    if request.method == 'POST':
        todo.title = request.form['title'].strip()
        todo.description = request.form['description'].strip()
        todo.status = True if request.form.get('status') == 'on' else False
        
        db.session.commit()

        message = {
            'message': 'Task successfully updated!!',
            'type': 'alert-success'
        }
        flash(message)

        return redirect(url_for('todo_views.index'))

    return render_template('todo/update.html', todo = todo)

@bp.route('/delete/<int:id>', methods=["DELETE"])
@login_required
def delete(id):
    db.session.delete(get_todo_by_id(id))
    db.session.commit()

    return render_template('todo/board.partial.html', **_board_context())

