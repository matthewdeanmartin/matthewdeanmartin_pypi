FROM python:3.12-slim

LABEL maintainer="john@example.com"
LABEL description="John Doe's PyPI profile website, served by pypi-profile."

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install pypi-profile and the profile data package together
RUN pip install --no-cache-dir "pypi-profile" "john-doe"

USER appuser

EXPOSE 8000

ENTRYPOINT ["pypi-profile", "serve", "john-doe"]
