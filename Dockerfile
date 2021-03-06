FROM python:3
USER root

RUN apt-get update
RUN apt-get -y install locales && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8
RUN apt-get -y install vim
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9
ENV TERM xterm

EXPOSE 443
EXPOSE 80

WORKDIR /usr/src/app
COPY requirements.txt ./
COPY ignore ./ignore
COPY Model ./Model
COPY Data ./Data
COPY *.py ./

#RUN wget https://github.com/Kitware/CMake/releases/download/v3.14.3/cmake-3.14.3.tar.gz && \
#  tar xvf cmake-3.14.3.tar.gz && \
#  cd cmake-3.14.3 && \
#  ./bootstrap && make && make install && make -j4
#RUN apt-get install -y vim less && \
#  git clone --recursive https://github.com/dmlc/xgboost.git && \
#  cd xgboost && \
#  make -j4
#RUN cd xgboost/python-package; python3 setup.py install && cd ../..
#RUN apt-get -y install cmake
  #mkdir build && \
  #cd build && \
  #cmake .. && \
  #cd .. && \
  #cd python-package && python3 setup.py install

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install numpy

RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -zxvf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/ec2-usr && \
    make && \
    make install && \
    cd ../
    #rm -rf ta-lib-0.4.0-src.tar.gz && \
    #rm -rf ta-lib

RUN pip install -r requirements.txt
CMD ["python","./Bot.py"]
