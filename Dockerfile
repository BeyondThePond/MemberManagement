FROM alpine/git:v2.26.2-amd64 AS version

ADD .git .git
RUN git describe --always > /PORTAL_VERSION
RUN echo "Saved version file containing '$(cat /PORTAL_VERSION)'"

# image for building node dependencies
FROM node:18-alpine AS frontend

RUN apk add --no-cache \
    git

# install node dependencies
ADD package.json /app/package.json
ADD yarn.lock /app/yarn.lock
WORKDIR /app/
RUN yarn install

# install frontend scripts + build
ADD tsconfig.json /app/tsconfig.json
ADD webpack.config.js /app/webpack.config.js
ADD assets/ /app/assets/
RUN yarn build

# image for python
FROM python:3.13-alpine

# Install binary python dependencies
RUN apk add --no-cache \
    build-base \
    mailcap \
    libxslt-dev \
    libffi-dev \
    linux-headers \
    pcre-dev \
    python3-dev

ADD docker/uwsgi.ini /app/uwsgi.ini

# Add requirements and install dependencies
ADD pyproject.toml /app/
ADD poetry.lock /app/
ADD requirements-prod.txt /app/
WORKDIR /app/

# install all the python runtime dependencies
RUN mkdir -p /var/www/static/ \
    && pip install -r requirements-prod.txt \
    && poetry config virtualenvs.create false \
    && poetry install --only main

# Install Django App and setup the setting module
ADD manage.py /app/
ADD alumni/ /app/alumni
ADD django_forms_uikit/ /app/django_forms_uikit
ADD MemberManagement/ /app/MemberManagement
ADD registry/ /app/registry/
ADD static/ /app/static/
ADD custom_auth/ /app/custom_auth
ADD atlas/ /app/atlas
ADD payments/ /app/payments
ADD docker/ /app/docker
ADD donations/ /app/donations
ADD donation_receipts/ /app/donation_receipts

# copy over the frontend assets
COPY --from=frontend /app/webpack-stats.json /app/webpack-stats.json
COPY --from=frontend /app/assets/bundles /app/assets/bundles/

# default settings are in MemberManagement
ENV DJANGO_SETTINGS_MODULE="MemberManagement.docker_settings"

### ALL THE CONFIGURATION

# disable / enable the devel warning shown on the page
ENV DJANGO_ENABLE_DEVEL_WARNING="1"

# The secret key used for django
ENV DJANGO_SECRET_KEY=""

# A comma-seperated list of allowed hosts
ENV DJANGO_ALLOWED_HOSTS="localhost"
ENV DJANGO_CSRF_ORIGINS="http://localhost:8000"

# Database settings
## Use SQLITE out of the box
ENV DJANGO_DB_ENGINE="django.db.backends.sqlite3"
ENV DJANGO_DB_NAME="/data/MemberManagment.db"
ENV DJANGO_DB_USER=""
ENV DJANGO_DB_PASSWORD=""
ENV DJANG_DB_HOST=""
ENV DJANGO_DB_PORT=""

# Stripe keys -- required
ENV STRIPE_SECRET_KEY=""
ENV STRIPE_PUBLISHABLE_KEY=""

ENV FINALIZE_AUTOMATICALLY="1"

# GSuite Auth file should be in the data volume
ENV GSUITE_AUTH_FILE=/data/credentials.json

# Raven -- optional
ENV DJANGO_RAVEN_DSN=""

# Collect all the static files at build time
RUN DJANGO_SECRET_KEY=setup python manage.py collectstatic --noinput

# Volume and ports
VOLUME /data/
EXPOSE 80

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "MemberManagement.asgi:application", "--host", "0.0.0.0", "--port", "80"]

COPY --from=version /PORTAL_VERSION /app/PORTAL_VERSION
