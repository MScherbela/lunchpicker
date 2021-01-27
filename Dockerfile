FROM python:3.8
WORKDIR /workdir
RUN apt-get update
RUN apt-get install vim less

# set-up the working dir (incl. the code) and install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt
#COPY app.py .
#ADD templates ./templates
#ADD static ./static

ENV FLASK_APP=app.py
CMD ["gunicorn", "--bind", ":80", "--worker-tmp-dir", "/dev/shm", "--workers=1", "--threads=2", "app:app"]
