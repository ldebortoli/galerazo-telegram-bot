FROM python:3.14.7-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd --gid 10001 galerazo \
    && useradd --uid 10001 --gid galerazo --create-home --home-dir /home/galerazo galerazo \
    && install -d -o galerazo -g galerazo /app/data /app/backups

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt

FROM base AS test

COPY --chown=galerazo:galerazo . .
USER galerazo

FROM base AS runtime

LABEL org.opencontainers.image.title="Galerazo Bot"
LABEL org.opencontainers.image.description="Bot de Telegram con persistencia SQLite"
LABEL org.opencontainers.image.source="https://github.com/ldebortoli/galerazo-telegram-bot"

COPY --chown=galerazo:galerazo app.py ./app.py
COPY --chown=galerazo:galerazo CHANGELOG.md ./CHANGELOG.md
COPY --chown=galerazo:galerazo .python-version ./.python-version
COPY --chown=galerazo:galerazo galerazo_bot ./galerazo_bot
COPY --chown=galerazo:galerazo mini_app ./mini_app
COPY --chown=galerazo:galerazo assets/hisopos ./assets/hisopos

EXPOSE 8080

USER galerazo

STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD ["python", "-m", "galerazo_bot.healthcheck"]

CMD ["python", "app.py"]
