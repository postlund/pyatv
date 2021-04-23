#!/bin/bash

run()
{
    docker run -p 4000:4000 --rm \
            -v "$PWD:/srv/jekyll" \
            -v "$PWD/docs/vendor/bundle:/usr/local/bundle" \
            -w /srv/jekyll/docs \
            -it jekyll/jekyll:3.8 "$@"
}

if [[ $GITPOD_INSTANCE_ID ]]; then
    cd docs && bundle install && bundle update github-pages && bundle exec jekyll serve --incremental --watch
else
    run bundle update github-pages
    run jekyll serve --incremental --watch
fi
