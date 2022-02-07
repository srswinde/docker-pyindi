FROM python:3.8-bullseye

LABEL maintainer="Scott Swindell <sswindell@mmto.org>"


WORKDIR /app
ADD . /app/


RUN apt update  \
		&& pip install --upgrade pip \
    && pip install wheel \
    && pip install tornado\
    && pip install tornado\
    && pip install pandas\
		&& pip install git+https://github.com/MMTObservatory/pyINDI \
		&& pip install git+https://github.com/srswinde/py2js

COPY pyindi-panel.html /usr/local/bin/pyindi/pyindi-panel.html
COPY example.py /usr/local/bin/pyindi/example.py

CMD python /usr/local/bin/pyindi/example.py

