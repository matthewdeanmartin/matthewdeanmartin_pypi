FROM python:3.12-slim

LABEL maintainer="{{ cookiecutter.author_email }}"
LABEL description="{{ cookiecutter.project_description }}"

WORKDIR /app

# Non-root user for runtime isolation
RUN useradd --create-home --shell /bin/bash appuser

# Install the package as root so the venv is system-wide, then drop to appuser
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir john_doe

# Drop privileges
USER appuser

# Default: show help.  Override CMD or pass arguments after the image name.
ENTRYPOINT ["john_doe"]
CMD ["--help"]
