FROM nikaro/debian-dev:latest

# local pyvenv to avoid conflicts with system
ENV PYVENV ${HOME}/pyvenv
# add pyvenv to path
ENV PATH ${PYVENV}/bin:${PATH}

RUN \
    sudo apt-get update && \
    sudo apt-get install --no-install-recommends --yes \
        python3-venv \
        && \
    sudo apt-get clean --yes && \
    sudo rm -rf /var/lib/apt/lists/* && \
    :

RUN \
    # create pyvenv
    python3 -m venv --system-site-packages ${PYVENV} && \
    # update pip tools into pyvenv
    pip install -U \
        pip \
        wheel \
        && \
    pip install -U \
        autopep8 \
        flake8 \
        && \
    :
