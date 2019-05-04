FROM ubuntu:latest
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt-get install -y \
    tzdata \
    git \
    build-essential \
    checkinstall \
    libreadline-gplv2-dev \
    libncursesw5-dev \
    libssl-dev \
    libsqlite3-dev \
    tk-dev \
    libgdbm-dev \
    libc6-dev \
    libbz2-dev \
    zlib1g-dev \
    openssl \
    libffi-dev \
    python3-dev \
    python3-setuptools \
    python-pip \
    wget \
    && mkdir /tmp/Python37
ENV TZ Asia/Tokyo
WORKDIR tmp/Python37
RUN wget https://www.python.org/ftp/python/3.7.0/Python-3.7.0.tar.xz \
    && tar xvf Python-3.7.0.tar.xz
WORKDIR /tmp/Python37/Python-3.7.0
RUN ./configure --enable-optimizations \
    && make altinstall \
    && mkdir /usr/local/app
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py
WORKDIR /usr/local/app

COPY requirements.txt ./
COPY ignore ./ignore
COPY Model ./Model
COPY Data ./Data
COPY btc-bot2 ./btc-bot2
COPY *.py ./
RUN source btc-bot2/bin/activate
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt
