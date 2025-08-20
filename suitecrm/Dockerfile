FROM php:8.1.33-apache-bullseye

ARG USERID
ARG GROUPID

# Force the www-data user and group in the container
# to match the external user and group IDs.
RUN groupmod -g ${GROUPID} www-data
RUN usermod -u ${USERID} www-data

# Update and install required packages.
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y curl git wget nano \
    openssl libfreetype-dev libjpeg62-turbo-dev libpng-dev libzip-dev zlib1g-dev libjpeg-dev

# Add additional PHP extensions.
RUN docker-php-ext-configure zip
RUN docker-php-ext-install zip
RUN docker-php-ext-enable zip
RUN docker-php-ext-configure gd --with-freetype --with-jpeg
RUN docker-php-ext-install gd
RUN docker-php-ext-enable gd
RUN docker-php-ext-configure mysqli
RUN docker-php-ext-install mysqli
RUN docker-php-ext-enable mysqli

# Install composer.
RUN wget https://raw.githubusercontent.com/composer/getcomposer.org/f3108f64b4e1c1ce6eb462b159956461592b3e3e/web/installer -O - -q | php -- --install-dir=/usr/bin/ --filename-composer --quiet

# Setup PHP configuration file.
RUN cp "$PHP_INI_DIR/php.ini-development" "$PHP_INI_DIR/php.ini"

WORKDIR /usr/local/etc/php
COPY php.ini.patch /usr/local/etc/php
RUN patch -u php.ini -i php.ini.patch

# Create upload folder.
RUN mkdir /var/www/html/upload

WORKDIR /var/www/html/