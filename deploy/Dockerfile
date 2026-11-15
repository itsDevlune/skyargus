FROM node:24-bookworm-slim AS assets
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY static ./static
COPY templates ./templates
RUN npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 ARGUS_DEBUG=0 ARGUS_DISPATCH=celery
WORKDIR /app
RUN useradd --uid 10001 --create-home argus
COPY requirements-linux.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements-linux.lock
COPY . .
COPY --from=assets /build/static/tailwind.css ./static/tailwind.css
RUN mkdir -p /app/data /app/staticfiles && chown -R argus:argus /app
USER argus
EXPOSE 8000
CMD ["gunicorn", "argus.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "40", "--access-logfile", "-", "--error-logfile", "-"]
