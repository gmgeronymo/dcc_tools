FROM tiangolo/uwsgi-nginx-flask:python3.11

COPY ./app/requirements.txt /root/

RUN pip install --no-cache-dir --upgrade -r /root/requirements.txt

