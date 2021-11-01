from fabric.api import task


@task
def hello():
    print("wonderful print")
