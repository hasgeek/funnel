from fabric.api import task, run

@task
def hello():
	print("wonderful print")