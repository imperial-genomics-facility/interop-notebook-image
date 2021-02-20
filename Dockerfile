FROM imperialgenomicsfacility/base-notebook-image:release-v0.0.5
LABEL maintainer="imperialgenomicsfacility"
LABEL version="0.0.1"
LABEL description="Docker image for running Interop data analysis"
ENV NB_USER vmuser
ENV NB_UID 1000
USER root
WORKDIR /
RUN apt-get -y update &&   \
    apt-get install --no-install-recommends -y \
      gcc \
      g++ \
      make \
      libgcc-5-dev \
      gfortran \
      pandoc \
      texlive-xetex \
      texlive-fonts-recommended \
      texlive-generic-recommended \
      texlive-generic-extra \
      fonts-lmodern \
      chromium-chromedriver \
      lmodern \
      gconf-service \
      libasound2 \
      libatk1.0-0 \
      libc6 \
      libcairo2 \
      libcups2 \
      libdbus-1-3 \
      libexpat1 \
      libfontconfig1 \
      libgcc1 \
      libgconf-2-4 \
      libgdk-pixbuf2.0-0 \
      libglib2.0-0 \
      libgtk-3-0 \
      libnspr4 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libstdc++6 \
      libx11-6 \
      libx11-xcb1 \
      libxcb1 \
      libxcomposite1 \
      libxcursor1 \
      libxdamage1 \
      libxext6 \
      libxfixes3 \
      libxi6 \
      libxrandr2 \
      libxrender1 \
      libxss1 \
      libxtst6 \
      ca-certificates \
      fonts-liberation \
      libappindicator1 \
      libnss3 \
      lsb-release \
      xdg-utils \
      git  && \
    apt-get purge -y --auto-remove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
USER $NB_USER
WORKDIR /home/$NB_USER
ENV TMPDIR=/home/$NB_USER/.tmp
ENV PATH=$PATH:/home/$NB_USER/miniconda3/bin/
RUN rm -f /home/$NB_USER/environment.yml && \
    rm -f /home/$NB_USER/Dockerfile
COPY environment.yml /home/$NB_USER/environment.yml
COPY Dockerfile /home/$NB_USER/Dockerfile
USER root
RUN chown ${NB_UID} /home/$NB_USER/environment.yml && \
    chown ${NB_UID} /home/$NB_USER/Dockerfile
USER $NB_USER
WORKDIR /home/$NB_USER
RUN conda update -n base -c defaults conda && \
    conda env update -q -n notebook-env --file /home/$NB_USER/environment.yml && \
    /home/vmuser/miniconda3/envs/notebook-env/bin/jupyter labextension install jupyterlab-plotly@4.14.3 && \
    /home/vmuser/miniconda3/envs/notebook-env/bin/jupyter labextension install @jupyter-widgets/jupyterlab-manager plotlywidget@4.14.3 && \
    conda clean -a -y && \
    rm -rf /home/$NB_USER/.cache && \
    rm -rf /tmp/* && \
    rm -rf ${TMPDIR} && \
    mkdir -p ${TMPDIR} && \
    mkdir -p /home/$NB_USER/.cache && \
    find miniconda3/ -type f -name *.pyc -exec rm -f {} \; 
EXPOSE 8888
EXPOSE 8080
CMD [ "notebook" ]
