FROM python:3.10-slim-bookworm

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

# Configure poetry to create virtual environments in the project.
# This is done to be compatible with how uv and PDM set up the venvs.
RUN poetry config virtualenvs.in-project true

# Ensure the latest pyright version is used within the container.
ENV PYRIGHT_PYTHON_FORCE_VERSION="latest"

EXPOSE 8888
ENTRYPOINT ["/bin/sh"]
