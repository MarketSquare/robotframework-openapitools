FROM python:3.13-slim-bookworm

# Update the certificates
RUN apt-get update && \
	apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates

# curl is universally used and not having it may results in silent errors
RUN apt-get update && \
    apt-get install -y  --no-install-recommends curl

# git is needed to install the shared keywords / libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends git

# build-essentials is used for some Python package installs
RUN apt-get update && \
    apt-get install -y  --no-install-recommends build-essential

# Tkinter is not part of the standard lib, but e.g. the RF Dialogs library depends on it
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-tk

#  tmp files cleanup
RUN	apt-get clean && \
	rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN	python -m pip install --upgrade pip

ENV POETRY_HOME="/opt/poetry"
ENV PATH="$PATH:$POETRY_HOME/bin"
RUN curl -sSL https://install.python-poetry.org | python3 -
RUN poetry self update

# Configure poetry to not create virtual environments.
# This is done to force package installation to the global Python install so that users
# other than the Docker root user have access to the installed packages.
RUN poetry config virtualenvs.create false

EXPOSE 8888
ENTRYPOINT ["/bin/sh"]
