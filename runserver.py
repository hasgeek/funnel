from website import app, models, init_for
init_for('dev')
models.db.create_all()
app.run('0.0.0.0', port=3000, debug=True)
