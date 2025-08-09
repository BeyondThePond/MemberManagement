# Member Management Portal

![Build Status](https://github.com/BeyondThePond/MemberManagement/workflows/CI/badge.svg)

The Django Application for managing Jacobs University Bremen Alumni Members.

In general it fulfills six purposes:

1. *Registration* of new Alumni Members
2. *Processing* of Applications
3. *Collection* of Membership fees
4. *Self-Updating* of Alumni Data
5. *Administration* of Alumni Data
6. *Searching* of Alumni Data

<small>(Side Note: If you can think of a good acronym for these, let me know)</small>

## Installing

The entire application can be run locally for a development setup and via [Docker](https://www.docker.com/) in production.
For local dependency versions, we make use of the [.tool-versions](./tool-versions) file provided by [asdf](https://asdf-vm.com/).

### Local Development Instance

To run a local instance, install Python 3.9, then clone this repository and afterwards set up a [virtual environment](https://docs.python.org/3/library/venv.html) as follows:

```bash
# install the right python as per asdf
asdf install

# Install poetry
pip install poetry

# Install dependencies
poetry install

# Install pre-commit hooks
pre-commit install

# Run migrations
python manage.py migrate
```

Afterwards install the frontend dependencies using [yarn](https://yarnpkg.com/):

```bash
yarn
```

Note that this is only tested using the NodeJS version specified in `.tool-versions`.


By default a local instance is then configured to store data in a local `db.sqlite3` database.
One needs to start the django app in two parts, one part building the frontend dependencies using:

```bash
yarn dev
```

and in a seperate terminal the normal django development server:

```bash
python manage.py runserver
```

If you'd like to generate donation receipts PDFs, also run this

```bash
 docker run -p 3000:3000 ghcr.io/kuboschek/pdf-render-server:master
```

If you'd like to also receive Stripe webhooks: Install the Stripe CLI.
**Make sure to set STRIPE_WEBHOOK_SECRET** in local_settings.py

Then run
```bash
 stripe listen --forward-to=http://localhost:8000/payments/webhook/
```

### Further Settings

In principle the settings can be found in [`settings.py`](MemberManagement/settings.py).
To enable easier debugging, it is configured to automatically import settings from a file called `MemberManagement/local_settings.py`.
This file is intended to contain local settings, such as session tokens, or external authentication credentials.
A template `local_settings.py` can be generated using [`python manage.py gen_local_settings`](MemberManagement/management/commands/gen_local_settings.py).
The file is also `.gitignore`d and should not be committed.

Notice that however because of external integrations, some features may not work as expected.
See the Configuration sections of the appropriate settings to configure.

### Deployment via Docker

It is also possible to deploy this application via [Docker](https://www.docker.com/).
This repository is automatically built as a [GitHub Package](https://github.com/users/beyondthepond/packages/container/package/membermanagement) for every push on the main and prod branches.
- for the `main` branch, use `ghcr.io/beyondthepond/membermanagement:latest`
- for the `prod` branch, use `ghcr.io/beyondthepond/membermanagement:prod`

For Docker purposes the configuration file `MemberManagement/docker_settings.py` is used.
By default, it also uses a local sqlite database.
All configuration can be set via environment variables, see [Dockerfile](Dockerfile) for details.

## Weekly jobs

To run the weekly jobs, use:

```bash
python manage.py runjobs weekly
```

## Code Structure

The code is layed out as any other Django app.
The entry point can be found in `MemberManagement`.

The following portal-related apps exist:

- `MemberManagement/` -- serves as an entry point, contains all static routes and base templates
- `registry/` -- user-facing registration + editing of data (purposes 1 + 4)
- `alumni/` -- admin-facing viewing + editing of data, contains core Alumni models (purpose 5)
- `custom_auth/` -- GSuite-integration, including login and approval (purpose 2)
- `payments/` -- Stripe + payments integration (purpose 3)
- `atlas/` -- user-facing search of atlas data (purpose 6)
The following independent apps also exist:

- `django_forms_uikit` -- rendering django forms using the uikit framework

## Tests

This project contains several integration tests to ensure that user-facing functionality works as intended.
These integration tests make use of [Selenium](https://docs.seleniumhq.org) and [django-selenium-clean](https://github.com/aptiko/django-selenium-clean).

In addition to integration tests, other unit tests also exist.
One non-feature related test is the CodeStyle test. This enforces PEP8-compliance except for maximum line length.

The integration tests run headless by default and support the following browsers:
- Chrome using [chromedriver](https://sites.google.com/a/chromium.org/chromedriver/) (default)
- Firefox using [geckodriver](https://github.com/mozilla/geckodriver) (set `SELENIUM_WEBDRIVER=firefox`)
- Safari (__highly experimental__, set `SELENIUM_WEBDRIVER=safari`)

To run tests make sure that development dependencies are installed and then run:

```
yarn build # ensure that static assets have been built
pytest # to run the tests
```

By default, the tests are running in headless mode.
To enforce a visible browser, instead use:

```bash
yarn build # ensure that static assets have been built
SELENIUM_HEADLESS=0 pytest # to run headless
```

When offline Stripe frontend tests might fail because they require a connection to Stripe Servers.
To work around this, you can set the `SKIP_STRIPE_TESTS` variable as follows:

```bash
yarn build
SKIP_STRIPE_TESTS=1 pytest
```

Travis CI runs Chrome and Firefox tests in headless mode after every commit.

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received [a copy of the GNU General Public License](./LICENSE)
along with this program.  If not, see <https://www.gnu.org/licenses/>.
